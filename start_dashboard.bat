@echo off
setlocal enabledelayedexpansion

:: Set the dashboard paths (original and alternative)
set "DASHBOARD_PATH_PT=G:\Drives compartilhados\INVESTIMENTOS\Quant\PerseveraHub"
set "DASHBOARD_PATH_EN=G:\Shared drives\INVESTIMENTOS\Quant\PerseveraHub"

:: First try with the Portuguese path
set "DASHBOARD_PATH=%DASHBOARD_PATH_PT%"
if not exist "%DASHBOARD_PATH%" (
    echo Portuguese path not found, trying English path...
    set "DASHBOARD_PATH=%DASHBOARD_PATH_EN%"
)

echo Starting Persevera Asset Management Dashboard...
cd /d "%DASHBOARD_PATH%"
if errorlevel 1 (
    echo Failed to change to dashboard directory: %DASHBOARD_PATH%
    pause
    exit /b 1
)

python -m streamlit run app.py
if errorlevel 1 (
    echo Error occurred while running the dashboard. Please check if Python and Streamlit are installed:
    echo 1. Make sure Python is installed and in your PATH
    echo 2. Install Streamlit by running: pip install streamlit
    pause
    exit /b 1
)

echo.
echo Dashboard completed successfully.
pause 