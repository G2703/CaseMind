# CaseMind Web API - Startup Script
# Activates virtual environment and starts the FastAPI server

# Activate virtual environment
& "$PSScriptRoot\..\venv\Scripts\Activate.ps1"

# Change to src directory
Set-Location $PSScriptRoot

# Start FastAPI server
Write-Host "Starting CaseMind Web API on http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

python run_api.py
