import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from time import monotonic, sleep

from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

_XVFB_DISPLAY = ":99"

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


def _configure_chrome_runtime_env(chrome_binary: str | None) -> None:
    if not chrome_binary or os.name == "nt":
        return

    chrome_dir = str(Path(chrome_binary).resolve().parent)
    current = os.environ.get("LD_LIBRARY_PATH", "")
    if chrome_dir not in current.split(":"):
        os.environ["LD_LIBRARY_PATH"] = f"{chrome_dir}:{current}" if current else chrome_dir


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
        _configure_chrome_runtime_env(chrome_binary)
    if chromedriver:
        os.environ["CHROMEDRIVER_PATH"] = chromedriver


def _ensure_browser_binaries() -> None:
    if find_chrome_binary() and find_chromedriver():
        _configure_chrome_runtime_env(find_chrome_binary())
        return

    if not (sys.platform.startswith("linux") or is_deploy_env()):
        return

    _run_install_script()
    _export_binary_env_vars()


_APT_BIN_PREFIXES = (
    "/layers/digitalocean_apt/apt/usr/bin",
    "/workspace/.apt/usr/bin",
    "/usr/bin",
)


def _find_system_binary(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for prefix in _APT_BIN_PREFIXES:
        candidate = f"{prefix}/{name}"
        if _is_usable_binary(candidate):
            return candidate
    return None


def _find_xvfb_binary() -> str | None:
    return _find_system_binary("Xvfb") or _find_system_binary("xvfb")


def _is_display_ready(display: str) -> bool:
    xdpyinfo = _find_system_binary("xdpyinfo")
    if not xdpyinfo:
        return False
    result = subprocess.run(
        [xdpyinfo, "-display", display],
        capture_output=True,
        timeout=3,
        check=False,
    )
    return result.returncode == 0


def _start_dbus_daemon() -> None:
    dbus_daemon = _find_system_binary("dbus-daemon")
    if not dbus_daemon:
        os.environ.setdefault("DBUS_SESSION_BUS_ADDRESS", "disabled:")
        return

    socket_dir = Path("/tmp/dbus")
    socket_dir.mkdir(parents=True, exist_ok=True)
    socket_path = socket_dir / "session.socket"
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={socket_path}"

    if socket_path.exists():
        return

    subprocess.Popen(
        [
            dbus_daemon,
            "--session",
            f"--address=unix:path={socket_path}",
            "--nofork",
            "--nopidfile",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    sleep(0.5)


def _ensure_dbus_session() -> None:
    if os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        return

    dbus_launch = _find_system_binary("dbus-launch")
    if dbus_launch:
        result = subprocess.run(
            [dbus_launch, "--sh-syntax"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip(";").strip("'").strip('"')
                if key in {"DBUS_SESSION_BUS_ADDRESS", "DISPLAY"} and value:
                    os.environ[key] = value
            if os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
                return

    _start_dbus_daemon()


def _ensure_display() -> None:
    if sys.platform == "win32" and not is_deploy_env():
        return

    if not (is_deploy_env() or sys.platform.startswith("linux")):
        return

    display = os.environ.get("DISPLAY")
    if display and _is_display_ready(display):
        _ensure_dbus_session()
        return

    xvfb = _find_xvfb_binary()
    if not xvfb:
        raise WebDriverException(
            "Xvfb não encontrado. O ComDinheiro exige navegador visível; "
            "adicione xvfb, dbus-x11 e x11-utils no Aptfile."
        )

    logger.info("Iniciando Xvfb em %s para suportar navegador visível no servidor.", _XVFB_DISPLAY)
    subprocess.Popen(
        [xvfb, _XVFB_DISPLAY, "-ac", "-screen", "0", "1920x1080x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    deadline = monotonic() + 10
    while monotonic() < deadline:
        if _is_display_ready(_XVFB_DISPLAY):
            os.environ["DISPLAY"] = _XVFB_DISPLAY
            _ensure_dbus_session()
            return
        sleep(0.2)

    os.environ["DISPLAY"] = _XVFB_DISPLAY
    _ensure_dbus_session()
    sleep(1)


def _chrome_user_data_dir() -> str:
    return tempfile.mkdtemp(prefix="chrome-profile-")


def build_chrome_options(*, user_data_dir: str | None = None) -> Options:
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--window-size=1920,1080")

    if is_deploy_env() or sys.platform.startswith("linux"):
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-seccomp-filter-sandbox")
        options.add_argument("--no-zygote")
        options.add_argument("--ozone-platform=x11")

    profile_dir = user_data_dir or _chrome_user_data_dir()
    options.add_argument(f"--user-data-dir={profile_dir}")

    chrome_binary = find_chrome_binary()
    if chrome_binary:
        options.binary_location = chrome_binary
    return options


def _chrome_missing_libs(chrome_binary: str | None) -> str | None:
    if not chrome_binary or os.name == "nt":
        return None
    ldd = _find_system_binary("ldd")
    if not ldd:
        return None
    result = subprocess.run(
        [ldd, chrome_binary],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env=os.environ.copy(),
    )
    missing = [line.strip() for line in result.stdout.splitlines() if "not found" in line]
    return "; ".join(missing) if missing else None


def _probe_chrome_binary(chrome_binary: str | None) -> str:
    if not chrome_binary:
        return "Chrome binary não encontrado."

    env = os.environ.copy()
    try:
        version = subprocess.run(
            [chrome_binary, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            env=env,
        )
        if version.returncode != 0:
            return (version.stderr or version.stdout or "Falha ao executar chrome --version.").strip()
        return (version.stdout or version.stderr).strip()
    except Exception as exc:
        return f"Falha ao executar chrome --version: {exc}"


def driver_diagnostics() -> dict[str, str | None]:
    chrome_binary = find_chrome_binary()
    _ensure_display()
    return {
        "platform": platform.platform(),
        "GOOGLE_CHROME_BIN": os.environ.get("GOOGLE_CHROME_BIN"),
        "CHROME_BIN": os.environ.get("CHROME_BIN"),
        "CHROMEDRIVER_PATH": os.environ.get("CHROMEDRIVER_PATH"),
        "DISPLAY": os.environ.get("DISPLAY"),
        "DBUS_SESSION_BUS_ADDRESS": os.environ.get("DBUS_SESSION_BUS_ADDRESS"),
        "LD_LIBRARY_PATH": os.environ.get("LD_LIBRARY_PATH"),
        "chrome_binary": chrome_binary,
        "chromedriver": find_chromedriver(),
        "xvfb": _find_xvfb_binary(),
        "dbus_launch": _find_system_binary("dbus-launch"),
        "dbus_daemon": _find_system_binary("dbus-daemon"),
        "deploy_env": str(is_deploy_env()),
        "project_root": str(_project_root()),
        "cwd": str(Path.cwd()),
        "chrome_version_probe": _probe_chrome_binary(chrome_binary),
        "chrome_missing_libs": _chrome_missing_libs(chrome_binary),
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
    if not find_chrome_binary() or not find_chromedriver():
        _raise_missing_driver_error()

    if is_deploy_env() or sys.platform.startswith("linux"):
        if not _find_xvfb_binary():
            raise WebDriverException(
                "Xvfb não encontrado no servidor. Adicione xvfb ao Aptfile."
            )

    probe_error = _probe_chrome_binary(find_chrome_binary())
    missing_libs = _chrome_missing_libs(find_chrome_binary())
    if missing_libs:
        raise WebDriverException(
            f"Chrome com bibliotecas ausentes: {missing_libs}"
        )
    if probe_error.startswith("Falha") or probe_error.startswith("Chrome binary"):
        raise WebDriverException(
            f"Chrome encontrado, mas não executa corretamente: {probe_error}"
        )


def create_chrome_driver() -> webdriver.Chrome:
    _ensure_browser_binaries()
    _ensure_display()

    chromedriver = find_chromedriver()
    chrome_binary = find_chrome_binary()
    _configure_chrome_runtime_env(chrome_binary)

    probe_error = _probe_chrome_binary(chrome_binary)
    missing_libs = _chrome_missing_libs(chrome_binary)
    if missing_libs:
        raise WebDriverException(f"Chrome com bibliotecas ausentes: {missing_libs}")
    if probe_error.startswith("Falha") or probe_error.startswith("Chrome binary"):
        raise WebDriverException(
            f"Chrome encontrado, mas não executa corretamente: {probe_error}"
        )

    options = build_chrome_options()
    chromedriver_log = tempfile.NamedTemporaryFile(prefix="chromedriver-", suffix=".log", delete=False)
    chromedriver_log_path = chromedriver_log.name
    chromedriver_log.close()

    if is_deploy_env() and (not chromedriver or not chrome_binary):
        _raise_missing_driver_error()

    try:
        if chromedriver:
            os.environ["SE_OFFLINE"] = "true"
            service = Service(executable_path=chromedriver, log_output=chromedriver_log_path)
            driver = webdriver.Chrome(service=service, options=options)
        elif not is_deploy_env():
            driver = webdriver.Chrome(options=options)
        else:
            _raise_missing_driver_error()
    except SessionNotCreatedException as exc:
        log_tail = ""
        try:
            log_tail = Path(chromedriver_log_path).read_text(encoding="utf-8", errors="replace")[-2000:]
        except OSError:
            log_tail = ""

        missing_libs = _chrome_missing_libs(chrome_binary)
        details = (
            f"DISPLAY={os.environ.get('DISPLAY')!r}, "
            f"LD_LIBRARY_PATH={os.environ.get('LD_LIBRARY_PATH')!r}, "
            f"DBUS_SESSION_BUS_ADDRESS={os.environ.get('DBUS_SESSION_BUS_ADDRESS')!r}"
        )
        if missing_libs:
            details += f"\nBibliotecas ausentes: {missing_libs}"
        if log_tail:
            details += f"\n\nChromedriver log (final):\n{log_tail}"
        raise WebDriverException(
            "Não foi possível iniciar o Chrome em modo visível. "
            f"{details}"
        ) from exc

    try:
        driver.command_executor.set_timeout(600)
    except AttributeError:
        driver.command_executor._conn.timeout = 600  # noqa: SLF001
    driver.set_page_load_timeout(600)
    return driver
