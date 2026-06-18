import io
import logging
import re
import zipfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from time import monotonic, sleep

import pandas as pd
import requests
from PyPDF2 import PdfReader
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.selenium_driver import create_chrome_driver

from persevera_tools.config.settings import Settings
from persevera_tools.db.fibery import read_fibery


logger = logging.getLogger(__name__)

COL_NAME = "Name"
COL_CYCLE = "Chave Ciclo"
COL_REPORT_URL = "Url-Report-Completo"

COMDINHEIRO_LOGIN_URL = "https://www.comdinheiro.com.br/login"
PDF_TRIGGER_SCRIPT = """
    if (window.json_pdf && document.getElementById('combo_estilo_pdf') && document.getElementById('combo_num_pdf')) {
        CallAjaxLinkText(
            'CREATE_LAMINA_PDF',
            JSON.stringify(window.json_pdf),
            'MeuExtrato001',
            document.getElementById('combo_estilo_pdf').value,
            document.getElementById('combo_num_pdf').value,
            'Meu Extrato',
            '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''
        );
    }
"""

ProgressCallback = Callable[[str, float | None], None]


def _notify(callback: ProgressCallback | None, message: str, fraction: float | None = None) -> None:
    logger.info(message)
    if callback:
        callback(message, fraction)


def get_reports_urls() -> pd.DataFrame:
    df = read_fibery(
        table_name="Inv-Asset Allocation/Relatórios Mandatos Exclusivos",
        include_fibery_fields=False,
    )
    df[COL_REPORT_URL] = df[COL_REPORT_URL].replace(to_replace="", value=None)
    return df[[COL_NAME, COL_CYCLE, COL_REPORT_URL]].dropna().head(2)


def get_report_period_label(df: pd.DataFrame) -> str:
    cycle = str(df[COL_CYCLE].iloc[0]).strip()
    parsed = datetime.strptime(cycle, "%Y-%m")
    return parsed.strftime("%Y%m")


def build_save_path(df: pd.DataFrame, base_dir: str | Path | None = None) -> Path:
    period_label = get_report_period_label(df)
    root = Path(base_dir) if base_dir else Path("Relatórios")
    save_path = root / period_label
    save_path.mkdir(parents=True, exist_ok=True)
    return save_path


def validate_comdinheiro_credentials(settings: Settings | None = None) -> None:
    settings = settings or Settings()
    username = getattr(settings, "COMDINHEIRO_USERNAME", None) or ""
    password = getattr(settings, "COMDINHEIRO_PASSWORD", None) or ""
    if not username.strip() or not password.strip():
        raise ValueError(
            "Credenciais do ComDinheiro não configuradas. "
            "Defina COMDINHEIRO_USERNAME e COMDINHEIRO_PASSWORD no ambiente ou secrets."
        )


def _is_report_tab(url: str, report_urls: set[str]) -> bool:
    normalized_url = url.rstrip("/")
    return any(
        normalized_url == report_url.rstrip("/")
        or normalized_url.startswith(f"{report_url.rstrip('/')}")
        for report_url in report_urls
    )


def _count_pdf_tabs(driver: WebDriver) -> int:
    current_handle = driver.current_window_handle
    pdf_count = 0
    try:
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            if "_ExtratoDinamico.pdf" in driver.current_url:
                pdf_count += 1
    finally:
        if current_handle in driver.window_handles:
            driver.switch_to.window(current_handle)
    return pdf_count


def _wait_for_pdf_tabs(
    driver: WebDriver,
    expected_count: int,
    callback: ProgressCallback | None = None,
    timeout: int = 180,
) -> int:
    deadline = monotonic() + timeout
    last_count = 0

    while monotonic() < deadline:
        last_count = _count_pdf_tabs(driver)
        if last_count >= expected_count:
            return last_count
        _notify(
            callback,
            f"Aguardando PDFs no navegador ({last_count}/{expected_count})...",
            None,
        )
        sleep(2)

    return last_count


def login_comdinheiro(driver: WebDriver, settings: Settings) -> None:
    driver.get(COMDINHEIRO_LOGIN_URL)
    wait = WebDriverWait(driver, 30)
    user_field = wait.until(EC.presence_of_element_located((By.ID, "textUser")))
    user_field.send_keys(settings.COMDINHEIRO_USERNAME)
    driver.find_element(By.ID, "textSenha").send_keys(settings.COMDINHEIRO_PASSWORD)
    driver.find_element(By.ID, "login").click()
    wait.until(EC.url_changes(COMDINHEIRO_LOGIN_URL))


def _requests_session_from_driver(driver: WebDriver) -> requests.Session:
    session = requests.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(cookie["name"], cookie["value"])
    return session


def open_report_tabs(
    driver: WebDriver,
    df: pd.DataFrame,
    callback: ProgressCallback | None = None,
) -> int:
    total = len(df)
    if total == 0:
        _notify(callback, "Nenhuma URL de relatório encontrada.")
        return 0

    wait = WebDriverWait(driver, 30)
    for index, (_, row) in enumerate(df.iterrows(), start=1):
        driver.execute_script("window.open(arguments[0], '_blank');", row[COL_REPORT_URL])
        driver.switch_to.window(driver.window_handles[-1])
        wait.until(lambda d: d.execute_script("return window.json_pdf != null"))
        sleep(1)
        _notify(
            callback,
            f"Abrindo relatório {index}/{total}: {row[COL_NAME]}...",
            index / total,
        )
    return total


def trigger_pdf_generation(
    driver: WebDriver,
    report_urls: set[str],
    callback: ProgressCallback | None = None,
) -> int:
    handles = list(driver.window_handles)
    total = len(handles)
    triggered = 0

    for index, window_handle in enumerate(handles, start=1):
        driver.switch_to.window(window_handle)
        current_url = driver.current_url
        if not _is_report_tab(current_url, report_urls):
            continue

        driver.execute_script(PDF_TRIGGER_SCRIPT)
        sleep(60)
        driver.close()
        triggered += 1
        _notify(callback, f"Gerando PDF {triggered}/{len(report_urls)}...", index / total)

    return triggered


def download_generated_pdfs(
    driver: WebDriver,
    save_path: Path,
    callback: ProgressCallback | None = None,
) -> list[Path]:
    session = _requests_session_from_driver(driver)
    pdf_handles: list[str] = []

    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if "_ExtratoDinamico.pdf" in driver.current_url:
            pdf_handles.append(handle)

    saved_files: list[Path] = []
    total = len(pdf_handles)

    for index, handle in enumerate(pdf_handles, start=1):
        driver.switch_to.window(handle)
        pdf_url = driver.current_url
        response = session.get(pdf_url, timeout=120)
        response.raise_for_status()

        file_path = save_path / pdf_url.split("/")[-1].split("?")[0]
        file_path.write_bytes(response.content)
        saved_files.append(file_path)
        driver.close()
        _notify(callback, f"Baixando PDF {index}/{total}...", index / total)

    return saved_files


def rename_pdfs_by_portfolio(save_path: Path, period_label: str, callback: ProgressCallback | None = None) -> list[Path]:
    if not save_path.is_dir():
        return []

    pdf_files = sorted(save_path.glob("*.pdf"))
    renamed_files: list[Path] = []

    for index, pdf_file in enumerate(pdf_files, start=1):
        try:
            with pdf_file.open("rb") as file:
                reader = PdfReader(file)
                text = "".join(page.extract_text() or "" for page in reader.pages)

            carteira_match = re.search(r"Carteira: (.{4})", text)
            if not carteira_match:
                logger.warning("Padrão 'Carteira:' não encontrado em %s.", pdf_file.name)
                renamed_files.append(pdf_file)
                continue

            new_filename = f"{period_label}_PERSEVERA_{carteira_match.group(1)}.pdf"
            new_file_path = save_path / new_filename
            if new_file_path != pdf_file:
                pdf_file.rename(new_file_path)
            renamed_files.append(new_file_path)
            _notify(
                callback,
                f"Renomeando PDF {index}/{len(pdf_files)}: {new_filename}",
                index / len(pdf_files),
            )
        except Exception as exc:
            logger.error("Não foi possível processar %s: %s", pdf_file.name, exc)
            renamed_files.append(pdf_file)

    return renamed_files


def build_reports_zip(save_path: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for pdf_file in sorted(save_path.glob("*.pdf")):
            archive.write(pdf_file, arcname=pdf_file.name)
    return buffer.getvalue()


def download_comdinheiro_reports(
    *,
    reports_df: pd.DataFrame | None = None,
    save_path: Path | None = None,
    callback: ProgressCallback | None = None,
) -> tuple[Path, list[Path]]:
    settings = Settings()
    validate_comdinheiro_credentials(settings)
    df = reports_df if reports_df is not None else get_reports_urls()

    if df.empty:
        raise ValueError("Nenhum relatório encontrado no Fibery.")

    period_label = get_report_period_label(df)
    target_path = save_path or build_save_path(df)
    target_path.mkdir(parents=True, exist_ok=True)
    report_urls = set(df[COL_REPORT_URL].astype(str))

    driver: WebDriver | None = None
    downloaded_files: list[Path] = []

    try:
        _notify(callback, "Iniciando navegador...", 0.0)
        driver = create_chrome_driver()

        _notify(callback, "Realizando login no ComDinheiro...", 0.05)
        login_comdinheiro(driver, settings)

        _notify(callback, "Abrindo páginas dos relatórios...", 0.1)
        open_report_tabs(driver, df, callback)

        _notify(callback, "Solicitando geração dos PDFs...", 0.4)
        triggered = trigger_pdf_generation(driver, report_urls, callback)
        if triggered == 0:
            raise ValueError("Nenhuma aba de relatório foi processada para gerar PDF.")

        _notify(callback, "Aguardando abas de PDF no navegador...", 0.55)
        pdf_tab_count = _wait_for_pdf_tabs(driver, len(report_urls), callback)
        if pdf_tab_count == 0:
            raise ValueError("Nenhuma aba de PDF foi aberta pelo ComDinheiro.")

        _notify(callback, "Baixando arquivos PDF...", 0.7)
        downloaded_files = download_generated_pdfs(driver, target_path, callback)

        _notify(callback, "Renomeando PDFs por carteira...", 0.9)
        renamed_files = rename_pdfs_by_portfolio(target_path, period_label, callback)
        _notify(callback, f"Download concluído: {len(renamed_files)} arquivo(s).", 1.0)
        return target_path, renamed_files
    except TimeoutException as exc:
        raise TimeoutException("Tempo esgotado durante o download dos relatórios.") from exc
    finally:
        if driver:
            driver.quit()
