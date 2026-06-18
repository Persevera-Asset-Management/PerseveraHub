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

XDPYINFO_BIN="$(_resolve_file "$(_resolve_executable xdpyinfo || true)" /layers/digitalocean_apt/apt/usr/bin/xdpyinfo /usr/bin/xdpyinfo)"
DISPLAY_READY=0
if [ -n "$DISPLAY" ] && [ -n "$XDPYINFO_BIN" ] && "$XDPYINFO_BIN" -display "$DISPLAY" >/dev/null 2>&1; then
    DISPLAY_READY=1
fi

if [ "$DISPLAY_READY" -eq 0 ]; then
    XVFB_BIN="$(_resolve_file "$(_resolve_executable Xvfb || true)" /layers/digitalocean_apt/apt/usr/bin/Xvfb /usr/bin/Xvfb)"
    if [ -n "$XVFB_BIN" ]; then
        "$XVFB_BIN" :99 -ac -screen 0 1920x1080x24 >/tmp/xvfb.log 2>&1 &
        export DISPLAY=:99
        sleep 2
        echo "Xvfb started on DISPLAY=$DISPLAY"
    else
        echo "WARNING: Xvfb not found."
    fi
fi

if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
    DBUS_LAUNCH="$(_resolve_file "$(_resolve_executable dbus-launch || true)" /layers/digitalocean_apt/apt/usr/bin/dbus-launch /usr/bin/dbus-launch)"
    if [ -n "$DBUS_LAUNCH" ]; then
        eval "$("$DBUS_LAUNCH" --sh-syntax)"
        echo "D-Bus session started via dbus-launch."
    else
        DBUS_DAEMON="$(_resolve_file "$(_resolve_executable dbus-daemon || true)" /layers/digitalocean_apt/apt/usr/bin/dbus-daemon /usr/bin/dbus-daemon)"
        if [ -n "$DBUS_DAEMON" ]; then
            mkdir -p /tmp/dbus
            export DBUS_SESSION_BUS_ADDRESS="unix:path=/tmp/dbus/session.socket"
            "$DBUS_DAEMON" --session --address="$DBUS_SESSION_BUS_ADDRESS" --nofork --nopidfile >/tmp/dbus.log 2>&1 &
            sleep 1
            echo "D-Bus session started via dbus-daemon."
        else
            export DBUS_SESSION_BUS_ADDRESS="disabled:"
            echo "WARNING: D-Bus not found; using disabled session."
        fi
    fi
fi

if [ -n "$CHROMEDRIVER_BIN" ]; then
    export CHROMEDRIVER_PATH="$CHROMEDRIVER_BIN"
    echo "Chromedriver binary: $CHROMEDRIVER_BIN"
else
    echo "WARNING: Chromedriver binary not found."
fi
