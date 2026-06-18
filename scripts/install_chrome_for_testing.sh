#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="${CHROME_FOR_TESTING_DIR:-${ROOT_DIR}/.chrome-for-testing}"
CHROME_BIN="${INSTALL_DIR}/chrome-linux64/chrome"
DRIVER_BIN="${INSTALL_DIR}/chromedriver-linux64/chromedriver"

if [ -x "$CHROME_BIN" ] && [ -x "$DRIVER_BIN" ]; then
    echo "Chrome for Testing already installed at ${INSTALL_DIR}"
    exit 0
fi

VERSION="${CHROME_FOR_TESTING_VERSION:-$(curl -fsSL https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE)}"
BASE_URL="https://storage.googleapis.com/chrome-for-testing-public/${VERSION}/linux64"

echo "Installing Chrome for Testing ${VERSION} into ${INSTALL_DIR}"

tmpdir="$(mktemp -d)"
cleanup() {
    rm -rf "$tmpdir"
}
trap cleanup EXIT

mkdir -p "${INSTALL_DIR}"

curl -fsSL "${BASE_URL}/chrome-linux64.zip" -o "${tmpdir}/chrome-linux64.zip"
curl -fsSL "${BASE_URL}/chromedriver-linux64.zip" -o "${tmpdir}/chromedriver-linux64.zip"

unzip -q "${tmpdir}/chrome-linux64.zip" -d "${INSTALL_DIR}"
unzip -q "${tmpdir}/chromedriver-linux64.zip" -d "${INSTALL_DIR}"

chmod +x "$CHROME_BIN" "$DRIVER_BIN"
echo "Chrome for Testing installed successfully."
