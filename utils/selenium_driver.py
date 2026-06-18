import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

logger = logging.getLogger(__name__)

_DEPLOY_PREFIXES = ("/app", "/workspace")
_WINDOWS_CHROME_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def is_deploy_env() -> bool:
    return any(Path(prefix).exists() for prefix in _DEPLOY_PREFIXES)


def _is_usable_binary(path: str | None) -> bool:
    if not path:
        return False
    file_path = Path(path)
    if not file_path.is_file():
        return False
    if os.name == "nt":
        return True
    return os.access(file_path, os.X_OK)


def _existing_file(*candidates: str | None) -> str | None:
    for path in candidates:
        if _is_usable_binary(path):
            return path
    return None


def _deploy_paths(*suffixes: str) -> list[str]:
    return [f"{prefix}{suffix}" for prefix in _DEPLOY_PREFIXES for suffix in suffixes]


def _chrome_for_testing_candidates(binary_name: str) -> list[str]:
    root = _project_root()
    cwd = Path.cwd()
    platform_dirs = {
        "linux": ("chrome-linux64", "chromedriver-linux64", "chrome", "chromedriver"),
        "windows": ("chrome-win64", "chromedriver-win64", "chrome.exe", "chromedriver.exe"),
        "darwin": ("chrome-mac-x64", "chromedriver-mac-x64", "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing", "chromedriver"),
    }

    system = sys.platform
    if system.startswith("linux"):
        dirs = platform_dirs["linux"]
    elif system == "win32":
        dirs = platform_dirs["windows"]
    elif system == "darwin":
        dirs = platform_dirs["darwin"]
    else:
        dirs = platform_dirs["linux"]

    chrome_dir, driver_dir, chrome_file, driver_file = dirs
    is_chrome = binary_name == "chrome"
    folder = chrome_dir if is_chrome else driver_dir
    filename = chrome_file if is_chrome else driver_file

    relative = f".chrome-for-testing/{folder}/{filename}"
    return [
        str(root / relative),
        str(cwd / relative),
        *_deploy_paths(f"/{relative}"),
    ]


def find_chrome_binary() -> str | None:
    return _existing_file(
        os.environ.get("GOOGLE_CHROME_BIN"),
        os.environ.get("CHROME_BIN"),
        *_WINDOWS_CHROME_PATHS,
        shutil.which("chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        *_chrome_for_testing_candidates("chrome"),
        *_deploy_paths(
            "/.chrome-for-testing/chrome-linux64/chrome",
            "/.apt/usr/bin/chromium",
            "/.apt/usr/bin/chromium-browser",
            "/.apt/usr/bin/google-chrome",
        ),
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    )


def find_chromedriver() -> str | None:
    return _existing_file(
        os.environ.get("CHROMEDRIVER_PATH"),
        shutil.which("chromedriver"),
        *_chrome_for_testing_candidates("chromedriver"),
        *_deploy_paths(
            "/.chrome-for-testing/chromedriver-linux64/chromedriver",
            "/.chromedriver/bin/chromedriver",
            "/.apt/usr/bin/chromedriver",
        ),
        "/usr/bin/chromedriver",
        "/usr/lib/chromium/chromedriver",
        "/usr/lib/chromium-browser/chromedriver",
    )


def _run_install_script() -> None:
    root = _project_root()
    if sys.platform == "win32":
        script = root / "scripts" / "install_chrome_for_testing.ps1"
        if not script.is_file():
            return
        logger.info("Instalando Chrome for Testing (Windows)...")
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)],
            cwd=root,
            check=False,
            timeout=600,
        )
        return

    script = root / "scripts" / "install_chrome_for_testing.sh"
    if not script.is_file():
        return
    logger.info("Instalando Chrome for Testing (Linux/macOS)...")
    subprocess.run(["bash", str(script)], cwd=root, check=False, timeout=600)


def _export_binary_env_vars() -> None:
    chrome_binary = find_chrome_binary()
    chromedriver = find_chromedriver()
    if chrome_binary:
        os.environ["GOOGLE_CHROME_BIN"] = chrome_binary
        os.environ["CHROME_BIN"] = chrome_binary
    if chromedriver:
        os.environ["CHROMEDRIVER_PATH"] = chromedriver


def _ensure_browser_binaries() -> None:
    if find_chrome_binary() and find_chromedriver():
        return

    if not (sys.platform.startswith("linux") or is_deploy_env()):
        return

    _run_install_script()
    _export_binary_env_vars()


def _ensure_display_if_needed(*, headless: bool) -> None:
    if headless or os.environ.get("DISPLAY"):
        return
    if not (is_deploy_env() or sys.platform.startswith("linux")):
        return
    if not shutil.which("Xvfb"):
        return

    logger.info("Iniciando Xvfb para suportar navegador visível no servidor.")
    subprocess.Popen(
        ["Xvfb", ":99", "-screen", "0", "1920x1080x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    os.environ["DISPLAY"] = ":99"


def build_chrome_options(*, headless: bool = True) -> Options:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--window-size=1920,1080")

    chrome_binary = find_chrome_binary()
    if chrome_binary:
        options.binary_location = chrome_binary
    return options


def driver_diagnostics() -> dict[str, str | None]:
    return {
        "platform": platform.platform(),
        "GOOGLE_CHROME_BIN": os.environ.get("GOOGLE_CHROME_BIN"),
        "CHROME_BIN": os.environ.get("CHROME_BIN"),
        "CHROMEDRIVER_PATH": os.environ.get("CHROMEDRIVER_PATH"),
        "DISPLAY": os.environ.get("DISPLAY"),
        "chrome_binary": find_chrome_binary(),
        "chromedriver": find_chromedriver(),
        "deploy_env": str(is_deploy_env()),
        "project_root": str(_project_root()),
        "cwd": str(Path.cwd()),
    }


def _raise_missing_driver_error() -> None:
    diagnostics = driver_diagnostics()
    details = "\n".join(f"- {key}: {value or 'não encontrado'}" for key, value in diagnostics.items())
    raise WebDriverException(
        "Chrome/Chromium ou chromedriver não encontrados.\n"
        "Na Digital Ocean App Platform, confira se o Aptfile está na raiz "
        "do repositório, se o build executou `bin/post_compile` e se o Run Command "
        "usa `. ./setup.sh &&` antes do streamlit.\n"
        "No Windows, instale o Google Chrome ou execute "
        "`powershell -ExecutionPolicy Bypass -File scripts/install_chrome_for_testing.ps1`.\n\n"
        f"Diagnóstico:\n{details}"
    )


def validate_selenium_environment() -> None:
    _ensure_browser_binaries()
    if find_chrome_binary() and find_chromedriver():
        return
    _raise_missing_driver_error()


def create_chrome_driver(*, headless: bool = True) -> webdriver.Chrome:
    _ensure_browser_binaries()
    _ensure_display_if_needed(headless=headless)

    chromedriver = find_chromedriver()
    chrome_binary = find_chrome_binary()
    options = build_chrome_options(headless=headless)

    if is_deploy_env() and (not chromedriver or not chrome_binary):
        _raise_missing_driver_error()

    if chromedriver:
        os.environ["SE_OFFLINE"] = "true"
        service = Service(executable_path=chromedriver)
        driver = webdriver.Chrome(service=service, options=options)
    elif not is_deploy_env():
        driver = webdriver.Chrome(options=options)
    else:
        _raise_missing_driver_error()

    try:
        driver.command_executor.set_timeout(600)
    except AttributeError:
        driver.command_executor._conn.timeout = 600  # noqa: SLF001
    driver.set_page_load_timeout(600)
    return driver
