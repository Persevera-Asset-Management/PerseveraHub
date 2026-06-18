#!/bin/bash

mkdir -p /workspace/.streamlit

if [ -n "$STREAMLIT_SECRETS" ]; then
    echo "$STREAMLIT_SECRETS" > /workspace/.streamlit/secrets.toml
    echo "secrets.toml written from STREAMLIT_SECRETS env var."
else
    echo "WARNING: STREAMLIT_SECRETS env var is not set. Streamlit secrets will not be available."
fi

_resolve_executable() {
    if command -v "$1" >/dev/null 2>&1; then
        command -v "$1"
        return 0
    fi
    return 1
}

_resolve_file() {
    for candidate in "$@"; do
        if [ -n "$candidate" ] && [ -x "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

CHROME_BIN="${GOOGLE_CHROME_BIN:-${CHROME_BIN:-}}"
if [ -z "$CHROME_BIN" ]; then
    CHROME_BIN="$(_resolve_executable chrome || true)"
fi
if [ -z "$CHROME_BIN" ]; then
    CHROME_BIN="$(_resolve_executable chromium || true)"
fi
if [ -z "$CHROME_BIN" ]; then
    CHROME_BIN="$(_resolve_executable chromium-browser || true)"
fi
if [ -z "$CHROME_BIN" ]; then
    CHROME_BIN="$(_resolve_file \
        /app/.chrome-for-testing/chrome-linux64/chrome \
        /workspace/.chrome-for-testing/chrome-linux64/chrome \
        /app/.apt/usr/bin/chromium \
        /workspace/.apt/usr/bin/chromium \
        /app/.apt/usr/bin/chromium-browser \
        /workspace/.apt/usr/bin/chromium-browser \
        /usr/bin/chromium \
        /usr/bin/chromium-browser || true)"
fi

CHROMEDRIVER_BIN="${CHROMEDRIVER_PATH:-}"
if [ -z "$CHROMEDRIVER_BIN" ]; then
    CHROMEDRIVER_BIN="$(_resolve_executable chromedriver || true)"
fi
if [ -z "$CHROMEDRIVER_BIN" ]; then
    CHROMEDRIVER_BIN="$(_resolve_file \
        /app/.chrome-for-testing/chromedriver-linux64/chromedriver \
        /workspace/.chrome-for-testing/chromedriver-linux64/chromedriver \
        /app/.chromedriver/bin/chromedriver \
        /workspace/.chromedriver/bin/chromedriver \
        /app/.apt/usr/bin/chromedriver \
        /workspace/.apt/usr/bin/chromedriver \
        /usr/bin/chromedriver \
        /usr/lib/chromium/chromedriver \
        /usr/lib/chromium-browser/chromedriver || true)"
fi

if [ -n "$CHROME_BIN" ]; then
    export GOOGLE_CHROME_BIN="$CHROME_BIN"
    export CHROME_BIN="$CHROME_BIN"
    echo "Chrome binary: $CHROME_BIN"
else
    echo "WARNING: Chrome/Chromium binary not found."
fi

if [ -n "$CHROMEDRIVER_BIN" ]; then
    export CHROMEDRIVER_PATH="$CHROMEDRIVER_BIN"
    echo "Chromedriver binary: $CHROMEDRIVER_BIN"
else
    echo "WARNING: Chromedriver binary not found."
fi
