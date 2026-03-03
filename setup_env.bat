@echo off
REM Photo_Matcher — Windows Environment Setup
REM Run this script from the project root: setup_env.bat

echo ============================================
echo  Photo_Matcher — Environment Setup (Windows)
echo ============================================
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
        exit /b 1
    )

    call photo_matcher_env\Scripts\activate.bat
    echo [INFO] Virtual environment activated.
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