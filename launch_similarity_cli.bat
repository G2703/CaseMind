@echo off
setlocal EnableDelayedExpansion

REM CaseMind Similarity Analyzer - Quick Launch Script
REM This script launches the Rich CLI in interactive mode

echo ========================================
echo CaseMind Similarity Analyzer
echo ========================================
echo.

REM Change to the script directory (where this .bat file is located)
cd /d "%~dp0"
echo Working directory: %CD%
echo.

REM Check for virtual environment
if exist "venv\Scripts\activate.bat" (
    echo Found virtual environment: venv
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
    echo Virtual environment activated
) else if exist ".venv\Scripts\activate.bat" (
    echo Found virtual environment: .venv
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
    echo Virtual environment activated
) else (
    echo [WARNING] No virtual environment found
    echo Looking for system Python...
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python is not installed or not in PATH!
        echo Please install Python and add it to your PATH
        echo Download from: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo [INFO] Using system Python (recommended to use virtual environment)
)

REM Display Python version
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Using: !PYTHON_VERSION!
echo.

REM Check if we're in the correct directory (look for key files)
if not exist "src\cli\rich_similarity_cli.py" (
    echo [ERROR] Cannot find CaseMind CLI script!
    echo Make sure this batch file is in the CaseMind root directory
    echo Expected file: src\cli\rich_similarity_cli.py
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Check if requirements file exists and install dependencies if needed
if exist "requirements.txt" (
    echo Found requirements.txt
    echo Checking if dependencies are installed...
    
    REM Check key dependencies quickly
    python -c "import rich, openai, sentence_transformers, numpy, sklearn" 2>nul
    if errorlevel 1 (
        echo [INFO] Some dependencies missing. Installing from requirements.txt...
        python -m pip install -r requirements.txt --quiet
        if errorlevel 1 (
            echo [ERROR] Failed to install dependencies from requirements.txt
            echo Please run manually: pip install -r requirements.txt
            pause
            exit /b 1
        )
        echo [SUCCESS] Dependencies installed from requirements.txt
    ) else (
        echo [SUCCESS] All required dependencies are already installed
    )
) else (
    echo [WARNING] requirements.txt not found
    echo Checking core dependencies manually...
    
    REM Quick check for essential packages
    python -c "import rich, openai" 2>nul
    if errorlevel 1 (
        echo [ERROR] Core dependencies missing (rich, openai)
        echo Please install requirements: pip install rich openai sentence-transformers numpy scikit-learn
        pause
        exit /b 1
    )
    echo [INFO] Core dependencies found
)
echo.

REM Check for config file
if not exist "config.json" (
    echo [WARNING] config.json not found in root directory
    echo The CLI will prompt for configuration or use defaults
    echo.
)

REM Check for .env file
if not exist ".env" (
    echo [WARNING] .env file not found
    echo Make sure to set OPENAI_API_KEY if using AI features
    echo.
)

REM Run the CLI
echo Starting CaseMind Similarity Analyzer...
echo ========================================
echo.

python src\cli\rich_similarity_cli.py

set CLI_EXIT_CODE=%errorlevel%

echo.
echo ========================================
if %CLI_EXIT_CODE% equ 0 (
    echo [SUCCESS] CaseMind CLI completed successfully
) else (
    echo [ERROR] CLI exited with error code: %CLI_EXIT_CODE%
    echo.
    echo Troubleshooting tips:
    echo 1. Check that all required files are present
    echo 2. Verify your OpenAI API key in .env file
    echo 3. Ensure embedding files exist in 'Embedding results' folder
    echo 4. Check that input PDF files are accessible
)

echo.
pause
