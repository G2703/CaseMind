@echo off
REM Batch script to run Weaviate ingestion pipeline

echo ====================================
echo CaseMind Weaviate Ingestion Pipeline
echo ====================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if Weaviate is running
echo Checking Weaviate connection...
curl -s http://localhost:8080/v1/.well-known/ready >nul 2>&1
if errorlevel 1 (
    echo ERROR: Weaviate is not running on http://localhost:8080
    echo.
    echo Please start Weaviate using Docker:
    echo   docker start weaviate
    echo.
    echo Or run the full Docker command:
    echo   docker run -d --name weaviate -p 8080:8080 -p 50051:50051 ^
    echo     -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true ^
    echo     -e PERSISTENCE_DATA_PATH=/var/lib/weaviate ^
    echo     -e DEFAULT_VECTORIZER_MODULE=none ^
    echo     -e ENABLE_MODULES=text2vec-openai ^
    echo     -e CLUSTER_HOSTNAME=node1 ^
    echo     semitechnologies/weaviate:latest
    echo.
    pause
    exit /b 1
)

echo Weaviate is running!
echo.

REM Parse command line arguments
if "%1"=="" goto menu
if /i "%1"=="init" goto init
if /i "%1"=="test" goto test
if /i "%1"=="ingest" goto ingest
if /i "%1"=="stats" goto stats
goto menu

:menu
echo What would you like to do?
echo.
echo [1] Initialize Weaviate collections
echo [2] Run test suite
echo [3] Ingest files
echo [4] Show collection statistics
echo [5] Exit
echo.
set /p choice="Enter choice (1-5): "

if "%choice%"=="1" goto init
if "%choice%"=="2" goto test
if "%choice%"=="3" goto ingest
if "%choice%"=="4" goto stats
if "%choice%"=="5" goto end
goto menu

:init
echo.
echo ====================================
echo Initializing Weaviate Collections
echo ====================================
echo.
python src\scripts\init_weaviate.py
echo.
pause
goto end

:test
echo.
echo ====================================
echo Running Test Suite
echo ====================================
echo.
python test_weaviate_pipeline.py
echo.
pause
goto end

:ingest
echo.
echo ====================================
echo Ingesting Files
echo ====================================
echo.
set /p dir="Enter directory path (or press Enter for cases/input_files): "
if "%dir%"=="" set dir=cases/input_files

if not exist "%dir%" (
    echo ERROR: Directory not found: %dir%
    pause
    goto end
)

echo Ingesting files from: %dir%
python ingest_cli.py ingest --directory "%dir%"
echo.
pause
goto end

:stats
echo.
echo ====================================
echo Collection Statistics
echo ====================================
echo.
python src\scripts\init_weaviate.py --stats
echo.
pause
goto end

:end
echo.
echo Done!
