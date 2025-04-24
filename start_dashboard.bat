@echo off
setlocal enabledelayedexpansion

:: Set the Anaconda path using current username
set "ANACONDA_PATH=C:\Users\%USERNAME%\anaconda3"

:: Set the dashboard paths (original and alternative)
set "DASHBOARD_PATH_PT=G:\Drives compartilhados\INVESTIMENTOS\Quant\PerseveraDashboard"
set "DASHBOARD_PATH_EN=G:\Shared drives\INVESTIMENTOS\Quant\PerseveraDashboard"

:: First try with the Portuguese path
set "DASHBOARD_PATH=%DASHBOARD_PATH_PT%"
if not exist "%DASHBOARD_PATH%" (
    echo Portuguese path not found, trying English path...
    set "DASHBOARD_PATH=%DASHBOARD_PATH_EN%"
)

:: Activate Anaconda environment
echo Activating Anaconda environment...
call "%ANACONDA_PATH%\Scripts\activate.bat"
if errorlevel 1 (
    echo Failed to activate Anaconda environment.
    pause
    exit /b 1
)

echo Starting Persevera Asset Management Dashboard...
cd /d "%DASHBOARD_PATH%"
if errorlevel 1 (
    echo Failed to change to dashboard directory: %DASHBOARD_PATH%
    pause
    exit /b 1
)

streamlit run app.py
if errorlevel 1 (
    echo Error occurred while running the dashboard
    pause
    exit /b 1
)

echo.
echo Dashboard completed successfully.
pause 