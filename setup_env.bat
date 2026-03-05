@echo off
REM ===========================================================================
REM Photo Matcher — Windows Environment Setup
REM Run from the project root: setup_env.bat
REM ===========================================================================

echo ============================================
echo  Photo Matcher — Environment Setup (Windows)
echo ============================================
echo.

REM Check if Python is available
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.11 or higher.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Display Python version
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [INFO] Found %PYTHON_VERSION%
echo.

REM Check if conda is available
where conda >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Conda detected. Setting up conda environment...
    echo.

    conda env create -f environment.yml
    if %ERRORLEVEL% NEQ 0 (
        echo [WARN] Environment may already exist. Updating...
        conda env update -f environment.yml --prune
    )

    echo.
    echo [SUCCESS] Setup complete!
    echo Run the following to get started:
    echo   conda activate photo_matcher_env
    echo   python main.py
) else (
    echo [INFO] Conda not found. Setting up pip virtual environment...
    echo.

    python -m venv photo_matcher_env
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        echo Make sure Python 3.11+ is installed.
        pause
        exit /b 1
    )

    call photo_matcher_env\Scripts\activate.bat
    echo [INFO] Virtual environment activated.

    echo [INFO] Upgrading pip...
    pip install --upgrade pip

    echo [INFO] Installing dependencies...
    echo.

    pip install -r requirements.txt

    echo.
    echo [SUCCESS] Setup complete!
    echo Run the following to get started:
    echo   photo_matcher_env\Scripts\activate
    echo   python main.py
)

echo.
pause