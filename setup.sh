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

_find_chrome_binary() {
    _resolve_file \
        "${GOOGLE_CHROME_BIN:-}" \
        "${CHROME_BIN:-}" \
        "$(_resolve_executable chrome || true)" \
        "$(_resolve_executable chromium || true)" \
        "$(_resolve_executable chromium-browser || true)" \
        "${PWD}/.chrome-for-testing/chrome-linux64/chrome" \
        /app/.chrome-for-testing/chrome-linux64/chrome \
        /workspace/.chrome-for-testing/chrome-linux64/chrome \
        /app/.apt/usr/bin/chromium \
        /workspace/.apt/usr/bin/chromium \
        /app/.apt/usr/bin/chromium-browser \
        /workspace/.apt/usr/bin/chromium-browser \
        /usr/bin/chromium \
        /usr/bin/chromium-browser
}

_find_chromedriver_binary() {
    _resolve_file \
        "${CHROMEDRIVER_PATH:-}" \
        "$(_resolve_executable chromedriver || true)" \
        "${PWD}/.chrome-for-testing/chromedriver-linux64/chromedriver" \
        /app/.chrome-for-testing/chromedriver-linux64/chromedriver \
        /workspace/.chrome-for-testing/chromedriver-linux64/chromedriver \
        /app/.chromedriver/bin/chromedriver \
        /workspace/.chromedriver/bin/chromedriver \
        /app/.apt/usr/bin/chromedriver \
        /workspace/.apt/usr/bin/chromedriver \
        /usr/bin/chromedriver \
        /usr/lib/chromium/chromedriver \
        /usr/lib/chromium-browser/chromedriver
}

CHROME_BIN="$(_find_chrome_binary || true)"
CHROMEDRIVER_BIN="$(_find_chromedriver_binary || true)"

if { [ -z "$CHROME_BIN" ] || [ -z "$CHROMEDRIVER_BIN" ]; } && [ -f "./scripts/install_chrome_for_testing.sh" ]; then
    echo "Chrome for Testing not found. Running install script..."
    bash ./scripts/install_chrome_for_testing.sh
    CHROME_BIN="$(_find_chrome_binary || true)"
    CHROMEDRIVER_BIN="$(_find_chromedriver_binary || true)"
fi

if [ -n "$CHROME_BIN" ]; then
    export GOOGLE_CHROME_BIN="$CHROME_BIN"
    export CHROME_BIN="$CHROME_BIN"
    CHROME_DIR="$(dirname "$CHROME_BIN")"
    export LD_LIBRARY_PATH="${CHROME_DIR}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    echo "Chrome binary: $CHROME_BIN"
else
    echo "WARNING: Chrome/Chromium binary not found."
fi

if [ -z "$DISPLAY" ] || ! xdpyinfo -display "${DISPLAY:-:99}" >/dev/null 2>&1; then
    if command -v Xvfb >/dev/null 2>&1; then
        Xvfb :99 -ac -screen 0 1920x1080x24 >/tmp/xvfb.log 2>&1 &
        export DISPLAY=:99
        sleep 2
        echo "Xvfb started on DISPLAY=$DISPLAY"
    else
        echo "WARNING: Xvfb not found."
    fi
fi

if [ -z "$DBUS_SESSION_BUS_ADDRESS" ] && command -v dbus-launch >/dev/null 2>&1; then
    eval "$(dbus-launch --sh-syntax)"
    echo "D-Bus session started."
fi

if [ -n "$CHROMEDRIVER_BIN" ]; then
    export CHROMEDRIVER_PATH="$CHROMEDRIVER_BIN"
    echo "Chromedriver binary: $CHROMEDRIVER_BIN"
else
    echo "WARNING: Chromedriver binary not found."
fi
