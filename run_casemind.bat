@echo off
REM CaseMind - Legal Case Similarity Search
REM Batch file to run the main application

echo.
echo Starting CaseMind...
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run the main Python application
python src\main.py

REM Pause to see any error messages
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to exit...
    pause >nul
)
