# CaseMind - PostgreSQL Setup Script for Windows
# This script automates PostgreSQL and pgvector installation/configuration

param(
    [switch]$SkipInstall,
    [string]$PostgresVersion = "16"
)

Write-Host "`n=== CaseMind PostgreSQL Setup ===" -ForegroundColor Cyan
Write-Host ""

# Function to check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Function to check if PostgreSQL is installed
function Test-PostgreSQLInstalled {
    $pgPath = Get-Command psql -ErrorAction SilentlyContinue
    return $null -ne $pgPath
}

# Function to check if pgvector is installed
function Test-PgVectorInstalled {
    try {
        $result = psql -U postgres -d postgres -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';" -t 2>$null
        return $result -match "vector"
    } catch {
        return $false
    }
}

# Check administrator privileges
if (-not (Test-Administrator)) {
    Write-Host "This script requires administrator privileges." -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    exit 1
}

# Step 1: Check PostgreSQL installation
Write-Host "[1/6] Checking PostgreSQL installation..." -ForegroundColor Cyan

if (Test-PostgreSQLInstalled) {
    Write-Host "  [OK] PostgreSQL is installed" -ForegroundColor Green
    
    # Get version
    $version = psql --version
    Write-Host "  Version: $version" -ForegroundColor Gray
} else {
    if ($SkipInstall) {
        Write-Host "  [ERROR] PostgreSQL is not installed" -ForegroundColor Red
        Write-Host "  Please install PostgreSQL manually or run without -SkipInstall flag" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "  [WARNING] PostgreSQL is not installed" -ForegroundColor Yellow
    Write-Host "  Installing PostgreSQL $PostgresVersion using Chocolatey..." -ForegroundColor Cyan
    
    # Check if Chocolatey is installed
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Host "  Installing Chocolatey package manager..." -ForegroundColor Cyan
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    }
    
    # Install PostgreSQL
    choco install postgresql$PostgresVersion -y
    
    # Refresh environment variables
    $machPath = [System.Environment]::GetEnvironmentVariable("Path","Machine")
    $userPath = [System.Environment]::GetEnvironmentVariable("Path","User")
    $env:Path = $machPath + ";" + $userPath
    
    Write-Host "  [OK] PostgreSQL installed" -ForegroundColor Green
}

Write-Host ""

# Step 2: Check PostgreSQL service
Write-Host "[2/6] Checking PostgreSQL service..." -ForegroundColor Cyan

$service = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1

if ($service) {
    if ($service.Status -eq "Running") {
        Write-Host "  [OK] PostgreSQL service is running" -ForegroundColor Green
    } else {
        Write-Host "  [WARNING] PostgreSQL service is stopped. Starting..." -ForegroundColor Yellow
        Start-Service $service.Name
        Write-Host "  [OK] PostgreSQL service started" -ForegroundColor Green
    }
} else {
    Write-Host "  [ERROR] PostgreSQL service not found" -ForegroundColor Red
    Write-Host "  Please check your PostgreSQL installation" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 3: Create database
Write-Host "[3/6] Creating CaseMind database..." -ForegroundColor Cyan

$dbExists = psql -U postgres -lqt 2>$null | Select-String -Pattern "casemind"

if ($dbExists) {
    Write-Host "  [OK] Database 'casemind' already exists" -ForegroundColor Green
} else {
    try {
        psql -U postgres -c "CREATE DATABASE casemind;" 2>$null
        Write-Host "  [OK] Database 'casemind' created" -ForegroundColor Green
    } catch {
        Write-Host "  [ERROR] Failed to create database" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# Step 4: Install pgvector
Write-Host "[4/6] Installing pgvector extension..." -ForegroundColor Cyan

# Download pgvector if needed
if (-not $SkipInstall) {
    Write-Host "  Downloading pgvector..." -ForegroundColor Gray
    
    # Get PostgreSQL installation directory
    $pgPath = (Get-Command psql).Source | Split-Path | Split-Path
    $pgVersion = (psql --version) -replace '[^\d.]', '' | Select-String -Pattern '^\d+' | ForEach-Object { $_.Matches.Value }
    
    # Download precompiled pgvector binary (if available)
    # Note: For production, compile from source or use prebuilt binaries
    Write-Host "  Installing pgvector (manual compilation may be required)" -ForegroundColor Yellow
    Write-Host "  For detailed instructions, see: https://github.com/pgvector/pgvector#windows" -ForegroundColor Gray
}

# Enable pgvector extension
Write-Host "  Enabling pgvector extension in database..." -ForegroundColor Gray

try {
    psql -U postgres -d casemind -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>$null
    Write-Host "  [OK] pgvector extension enabled" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Failed to enable pgvector extension" -ForegroundColor Red
    Write-Host "  You may need to compile pgvector from source" -ForegroundColor Yellow
    Write-Host "  See: https://github.com/pgvector/pgvector#installation" -ForegroundColor Gray
}

Write-Host ""

# Step 5: Initialize database schema
Write-Host "[5/6] Initializing database schema..." -ForegroundColor Cyan

try {
    python src/scripts/init_database.py
} catch {
    Write-Host "  [ERROR] Schema initialization failed" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    Write-Host "  Please run manually: python src/scripts/init_database.py" -ForegroundColor Yellow
}

Write-Host ""

# Step 6: Verify setup
Write-Host "[6/6] Verifying setup..." -ForegroundColor Cyan

$verified = $true

# Check database connection
try {
    $result = psql -U postgres -d casemind -c "SELECT 1;" -t 2>$null
    if ($result -match "1") {
        Write-Host "  [OK] Database connection successful" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Database connection failed" -ForegroundColor Red
        $verified = $false
    }
} catch {
    Write-Host "  [ERROR] Database connection failed" -ForegroundColor Red
    $verified = $false
}

# Check pgvector
try {
    $result = psql -U postgres -d casemind -c "SELECT * FROM pg_extension WHERE extname = 'vector';" -t 2>$null
    if ($result -match "vector") {
        Write-Host "  [OK] pgvector extension verified" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] pgvector extension not found" -ForegroundColor Red
        $verified = $false
    }
} catch {
    Write-Host "  [ERROR] pgvector verification failed" -ForegroundColor Red
    $verified = $false
}

# Check schema
try {
    $result = psql -U postgres -d casemind -c "\dt" -t 2>$null
    if ($result -match "documents") {
        Write-Host "  [OK] Database schema verified" -ForegroundColor Green
    } else {
        Write-Host "  [WARNING] Database schema not found (may need manual initialization)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [WARNING] Schema verification skipped" -ForegroundColor Yellow
}

Write-Host ""

# Final summary
if ($verified) {
    Write-Host "" 
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  [SUCCESS] Setup completed successfully!  " -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Copy .env.example to .env and configure settings" -ForegroundColor White
    Write-Host "  2. Install Python dependencies: pip install -r requirements.txt" -ForegroundColor White
    Write-Host "  3. Run the application: python src/main.py" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Yellow
    Write-Host "  [WARNING] Setup completed with warnings  " -ForegroundColor Yellow
    Write-Host "============================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please review the warnings above and fix any issues." -ForegroundColor Yellow
}

Write-Host ""
