#!/usr/bin/env bash
# ===========================================================================
# Photo Matcher — Linux/macOS Environment Setup
# Run from the project root: ./setup_env.sh
# ===========================================================================

set -e

echo "============================================"
echo " Photo Matcher — Environment Setup"
echo "============================================"
echo ""

# Check Python version
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python not found. Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "[INFO] Found $PYTHON_CMD ($PYTHON_VERSION)"
echo ""

# Check if conda is available
if command -v conda &> /dev/null; then
    echo "[INFO] Conda detected. Setting up conda environment..."
    echo ""

    conda env create -f environment.yml 2>/dev/null || {
        echo "[WARN] Environment may already exist. Updating..."
        conda env update -f environment.yml --prune
    }

    echo ""
    echo "[SUCCESS] Setup complete!"
    echo "Run the following to get started:"
    echo "  conda activate photo_matcher_env"
    echo "  $PYTHON_CMD main.py"
else
    echo "[INFO] Conda not found. Setting up pip virtual environment..."
    echo ""

    # Create virtual environment
    $PYTHON_CMD -m venv photo_matcher_env
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create virtual environment."
        echo "Make sure Python 3.11+ is installed with the venv module."
        echo ""
        echo "On Ubuntu/Debian, you may need:"
        echo "  sudo apt install python3-venv"
        exit 1
    fi

    # Activate
    source photo_matcher_env/bin/activate
    echo "[INFO] Virtual environment activated."

    # Upgrade pip
    echo "[INFO] Upgrading pip..."
    pip install --upgrade pip

    # Install dependencies
    echo "[INFO] Installing dependencies..."
    echo ""
    pip install -r requirements.txt

    echo ""
    echo "[SUCCESS] Setup complete!"
    echo "Run the following to get started:"
    echo "  source photo_matcher_env/bin/activate"
    echo "  $PYTHON_CMD main.py"
fi

echo ""