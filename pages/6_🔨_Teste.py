import os
import shutil
from pathlib import Path

import streamlit as st
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

_DEPLOY_PREFIXES = ("/app", "/workspace")


def _is_deploy_env() -> bool:
    return any(Path(prefix).exists() for prefix in _DEPLOY_PREFIXES)


def _existing_file(*candidates: str | None) -> str | None:
    for path in candidates:
        if path and Path(path).is_file():
            return path
    return None


def _deploy_paths(*suffixes: str) -> list[str]:
    return [f"{prefix}{suffix}" for prefix in _DEPLOY_PREFIXES for suffix in suffixes]


def _find_chrome_binary() -> str | None:
    return _existing_file(
        os.environ.get("GOOGLE_CHROME_BIN"),
        os.environ.get("CHROME_BIN"),
        shutil.which("chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        *_deploy_paths(
            "/.chrome-for-testing/chrome-linux64/chrome",
            "/.apt/usr/bin/chromium",
            "/.apt/usr/bin/chromium-browser",
            "/.apt/usr/bin/google-chrome",
        ),
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    )


def _find_chromedriver() -> str | None:
    return _existing_file(
        os.environ.get("CHROMEDRIVER_PATH"),
        shutil.which("chromedriver"),
        *_deploy_paths(
            "/.chrome-for-testing/chromedriver-linux64/chromedriver",
            "/.chromedriver/bin/chromedriver",
            "/.apt/usr/bin/chromedriver",
        ),
        "/usr/bin/chromedriver",
        "/usr/lib/chromium/chromedriver",
        "/usr/lib/chromium-browser/chromedriver",
    )


def _build_chrome_options() -> Options:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    chrome_binary = _find_chrome_binary()
    if chrome_binary:
        options.binary_location = chrome_binary
    return options


def _driver_diagnostics() -> dict[str, str | None]:
    return {
        "GOOGLE_CHROME_BIN": os.environ.get("GOOGLE_CHROME_BIN"),
        "CHROME_BIN": os.environ.get("CHROME_BIN"),
        "CHROMEDRIVER_PATH": os.environ.get("CHROMEDRIVER_PATH"),
        "chrome_binary": _find_chrome_binary(),
        "chromedriver": _find_chromedriver(),
        "deploy_env": str(_is_deploy_env()),
    }


def _raise_missing_driver_error() -> None:
    diagnostics = _driver_diagnostics()
    details = "\n".join(f"- {key}: {value or 'não encontrado'}" for key, value in diagnostics.items())
    raise WebDriverException(
        "Chrome/Chromium ou chromedriver não encontrados no servidor.\n"
        "Na Digital Ocean App Platform, confira se o arquivo Aptfile está na raiz "
        "do repositório e faça um redeploy.\n\n"
        f"Diagnóstico:\n{details}"
    )


@st.cache_resource
def get_driver():
    chromedriver = _find_chromedriver()
    chrome_binary = _find_chrome_binary()

    if _is_deploy_env() and (not chromedriver or not chrome_binary):
        _raise_missing_driver_error()

    if not chromedriver:
        raise WebDriverException(
            "Chromedriver não encontrado. Instale chromium-chromedriver via Aptfile "
            "(Digital Ocean) ou packages.txt (dev local) e faça redeploy."
        )

    os.environ["SE_OFFLINE"] = "true"
    service = Service(executable_path=chromedriver)
    return webdriver.Chrome(service=service, options=_build_chrome_options())


st.title("Streamlit and Selenium Integration")
url = st.text_input("Enter a URL to scrape:", "http://example.com")

with st.expander("Diagnóstico do ambiente Selenium", expanded=False):
    for key, value in _driver_diagnostics().items():
        st.write(f"**{key}:** {value or 'não encontrado'}")

if st.button("Scrape"):
    try:
        driver = get_driver()
        driver.get(url)
        st.write("Page Title:", driver.title)
        st.code(driver.page_source)
    except WebDriverException as exc:
        st.error(
            "Não foi possível iniciar o Chrome/Chromium no servidor. "
            "Na Digital Ocean, confira se o Aptfile está na raiz do repositório, "
            "se o Run Command executa setup.sh e faça um redeploy."
        )
        st.exception(exc)
