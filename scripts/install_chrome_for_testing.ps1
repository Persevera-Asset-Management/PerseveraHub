$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$InstallDir = if ($env:CHROME_FOR_TESTING_DIR) { $env:CHROME_FOR_TESTING_DIR } else { Join-Path $RootDir ".chrome-for-testing" }
$ChromeBin = Join-Path $InstallDir "chrome-win64\chrome.exe"
$DriverBin = Join-Path $InstallDir "chromedriver-win64\chromedriver.exe"

if ((Test-Path $ChromeBin) -and (Test-Path $DriverBin)) {
    Write-Host "Chrome for Testing already installed at $InstallDir"
    exit 0
}

$Version = if ($env:CHROME_FOR_TESTING_VERSION) {
    $env:CHROME_FOR_TESTING_VERSION
} else {
    (curl.exe -fsSL "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE").Trim()
}

$BaseUrl = "https://storage.googleapis.com/chrome-for-testing-public/$Version/win64"
$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("chrome-for-testing-" + [guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

try {
    Write-Host "Installing Chrome for Testing $Version into $InstallDir"
    $ChromeZip = Join-Path $TempDir "chrome-win64.zip"
    $DriverZip = Join-Path $TempDir "chromedriver-win64.zip"

    Invoke-WebRequest -Uri "$BaseUrl/chrome-win64.zip" -OutFile $ChromeZip
    Invoke-WebRequest -Uri "$BaseUrl/chromedriver-win64.zip" -OutFile $DriverZip

    Expand-Archive -Path $ChromeZip -DestinationPath $InstallDir -Force
    Expand-Archive -Path $DriverZip -DestinationPath $InstallDir -Force

    Write-Host "Chrome for Testing installed successfully."
}
finally {
    Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue
}
