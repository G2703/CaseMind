@echo off
REM CaseMind: Start static server and open the viewer
SETLOCAL ENABLEDELAYEDEXPANSION

REM --- Configuration ---
SET PORT=8001

REM Determine this script directory and repo root (parent folder)
SET SCRIPT_DIR=%~dp0
IF "%SCRIPT_DIR:~-1%"=="\" SET SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

PUSHD "%SCRIPT_DIR%\.."

REM If a cmd-style virtualenv activation exists, activate it (optional)
IF EXIST "venv\Scripts\activate.bat" (
  CALL "venv\Scripts\activate.bat"
)

REM Start a Python http.server in a new window so it keeps running
START "CaseMind Server" cmd /c "python -m http.server %PORT%"

REM Small pause to let the server bind
PING 127.0.0.1 -n 2 >NUL

REM Open the default browser to the viewer page
START "" "http://localhost:%PORT%/case_template_representation/index.html"

POPD
ENDLOCAL
EXIT /B 0
