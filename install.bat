@echo off
:: BanditCLI Installer for Windows
:: This script installs all required dependencies for BanditCLI using uv

setlocal enabledelayedexpansion

:: Set color variables
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "DEL=%%a"
set "RED=!DEL! [0;31m"
set "GREEN=!DEL! [0;32m"
set "YELLOW=!DEL! [0;33m"
set "BLUE=!DEL! [0;34m"
set "PURPLE=!DEL! [0;35m"
set "CYAN=!DEL! [0;36m"
set "WHITE=!DEL! [0;37m"
set "RESET=!DEL! [0m"

:: Function to print with color
:colorPrint
  echo %~2!%~1!%~3%RESET%
  exit /b

:: Print header
echo.
call :colorPrint "PURPLE" "" "=========================================================="
call :colorPrint "PURPLE" "" "          BanditCLI Windows Installer (uv)"
call :colorPrint "PURPLE" "" "=========================================================="
call :colorPrint "WHITE" "" "This will set up BanditCLI with uv for package management."
echo.

:: Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    call :colorPrint "RED" "" "[ERROR] Python is not installed or not in PATH."
    call :colorPrint "YELLOW" "" "Please install Python 3.7 or later from https://www.python.org/downloads/"
    call :colorPrint "YELLOW" "" "Make sure to check 'Add Python to PATH' during installation."
    pause
    exit /b 1
)

:: Get Python version
for /f "tokens=2" %%a in ('python --version 2^>^&1 ^| findstr /i "python"') do set "PYTHON_VERSION=%%a"
call :colorPrint "CYAN" "" "Found Python version: %PYTHON_VERSION%"

:: Check Python version
for /f "tokens=1-3 delims=." %%a in ("%PYTHON_VERSION%") do (
    if %%a LSS 3 (
        call :colorPrint "RED" "" "[ERROR] Python 3.7 or later is required."
        pause
        exit /b 1
    )
    if %%a EQU 3 if %%b LSS 7 (
        call :colorPrint "RED" "" "[ERROR] Python 3.7 or later is required."
        pause
        exit /b 1
    )
)

:: Install or update uv
call :colorPrint "BLUE" "" "Setting up uv..."
python -m pip install --upgrade uv
if %ERRORLEVEL% NEQ 0 (
    call :colorPrint "RED" "" "[ERROR] Failed to install uv."
    call :colorPrint "YELLOW" "" "Please try running this script as administrator."
    pause
    exit /b 1
)

:: Create or use existing .venv
if not exist ".venv\" (
    call :colorPrint "BLUE" "" "Creating virtual environment..."
    uv venv
    if %ERRORLEVEL% NEQ 0 (
        call :colorPrint "RED" "" "[ERROR] Failed to create virtual environment."
        pause
        exit /b 1
    )
    call :colorPrint "GREEN" "" "Virtual environment created."
) else (
    call :colorPrint "CYAN" "" "Using existing virtual environment."
)

:: Install dependencies
call :colorPrint "BLUE" "" "Installing dependencies using uv..."
uv pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    call :colorPrint "RED" "" "[ERROR] Failed to install dependencies."
    call :colorPrint "YELLOW" "" "Please check your internet connection and try again."
    pause
    exit /b 1
)

:: Verify installation
call :colorPrint "BLUE" "" "Verifying installation..."
.venv\Scripts\python.exe verify_installation.py
if %ERRORLEVEL% NEQ 0 (
    call :colorPrint "YELLOW" "" "Some issues were found during verification."
    call :colorPrint "YELLOW" "" "Check the output above for details."
    pause
    exit /b 1
)

:: Create a run script that uses the virtual environment
(
    echo @echo off
    echo :: Run BanditCLI with the virtual environment
    echo .venv\Scripts\python.exe run.py %%*
) > run.bat

:: Success
call :colorPrint "GREEN" "" "\nInstallation completed successfully!"
call :colorPrint "WHITE" "" "You can now run BanditCLI using 'run.bat'"
call :colorPrint "CYAN" "" "Virtual environment: .venv"
echo.
pause

endlocal
exit /b 0
