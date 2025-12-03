# CaseMind Weaviate Pipeline - PowerShell Helper
# Quick commands for common pipeline operations

param(
    [Parameter(Position=0)]
    [ValidateSet('init', 'test', 'ingest', 'stats', 'search', 'verify', 'help')]
    [string]$Command = 'help',
    
    [Parameter(Position=1)]
    [string]$Path,
    
    [string]$Pattern = '*.pdf',
    [string]$Query,
    [string]$FileId,
    [int]$Limit = 5,
    [switch]$Force
)

# Colors for output
function Write-Success { Write-Host "✓ $args" -ForegroundColor Green }
function Write-Error { Write-Host "✗ $args" -ForegroundColor Red }
function Write-Warning { Write-Host "⚠ $args" -ForegroundColor Yellow }
function Write-Info { Write-Host "ℹ $args" -ForegroundColor Cyan }

# Check Python
function Test-Python {
    try {
        $null = python --version 2>&1
        return $true
    } catch {
        return $false
    }
}

# Check Weaviate
function Test-Weaviate {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/v1/.well-known/ready" -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

# Show help
function Show-Help {
    Write-Host @"

CaseMind Weaviate Pipeline - PowerShell Helper
===============================================

USAGE:
    .\run_weaviate.ps1 <command> [options]

COMMANDS:
    init                Initialize Weaviate collections
    test                Run test suite
    ingest              Ingest files into Weaviate
    stats               Show collection statistics
    search              Search sections semantically
    verify              Verify file ingestion
    help                Show this help message

EXAMPLES:
    # Initialize collections
    .\run_weaviate.ps1 init

    # Force recreate collections
    .\run_weaviate.ps1 init -Force

    # Run tests
    .\run_weaviate.ps1 test

    # Ingest single file
    .\run_weaviate.ps1 ingest -Path "cases\input_files\case1.pdf"

    # Ingest directory
    .\run_weaviate.ps1 ingest -Path "cases\input_files"

    # Ingest with pattern
    .\run_weaviate.ps1 ingest -Path "cases\input_files" -Pattern "*.pdf"

    # Show statistics
    .\run_weaviate.ps1 stats

    # Search sections
    .\run_weaviate.ps1 search -Query "what are the facts" -Limit 10

    # Verify file
    .\run_weaviate.ps1 verify -FileId "abc123..."

"@ -ForegroundColor White
}

# Initialize collections
function Initialize-Collections {
    Write-Info "Initializing Weaviate collections..."
    
    if ($Force) {
        python src\scripts\init_weaviate.py --force
    } else {
        python src\scripts\init_weaviate.py
    }
}

# Run tests
function Run-Tests {
    Write-Info "Running test suite..."
    python test_weaviate_pipeline.py
}

# Ingest files
function Invoke-Ingestion {
    if (-not $Path) {
        $Path = "cases\input_files"
        Write-Warning "No path specified, using default: $Path"
    }
    
    if (-not (Test-Path $Path)) {
        Write-Error "Path not found: $Path"
        return
    }
    
    if (Test-Path $Path -PathType Leaf) {
        # Single file
        Write-Info "Ingesting file: $Path"
        python ingest_cli.py ingest --file "$Path"
    } else {
        # Directory
        Write-Info "Ingesting files from: $Path (pattern: $Pattern)"
        python ingest_cli.py ingest --directory "$Path" --pattern "$Pattern"
    }
}

# Show statistics
function Show-Statistics {
    Write-Info "Fetching collection statistics..."
    python src\scripts\init_weaviate.py --stats
}

# Search sections
function Search-Sections {
    if (-not $Query) {
        Write-Error "Query is required. Use: -Query 'your search query'"
        return
    }
    
    Write-Info "Searching for: '$Query'"
    python ingest_cli.py search --query "$Query" --limit $Limit
}

# Verify file
function Verify-File {
    if (-not $FileId) {
        Write-Error "File ID is required. Use: -FileId 'your-file-id'"
        return
    }
    
    Write-Info "Verifying file: $FileId"
    python ingest_cli.py verify --file-id "$FileId"
}

# Main execution
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "CaseMind Weaviate Pipeline" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
if (-not (Test-Python)) {
    Write-Error "Python is not installed or not in PATH"
    exit 1
}

if (-not (Test-Weaviate)) {
    Write-Warning "Weaviate is not running on http://localhost:8080"
    Write-Host ""
    Write-Host "Start Weaviate with Docker:" -ForegroundColor Yellow
    Write-Host "  docker start weaviate" -ForegroundColor White
    Write-Host ""
    Write-Host "Or run the full command:" -ForegroundColor Yellow
    Write-Host "  docker run -d --name weaviate -p 8080:8080 -p 50051:50051 ``" -ForegroundColor White
    Write-Host "    -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true ``" -ForegroundColor White
    Write-Host "    -e PERSISTENCE_DATA_PATH=/var/lib/weaviate ``" -ForegroundColor White
    Write-Host "    -e DEFAULT_VECTORIZER_MODULE=none ``" -ForegroundColor White
    Write-Host "    -e ENABLE_MODULES=text2vec-openai ``" -ForegroundColor White
    Write-Host "    -e CLUSTER_HOSTNAME=node1 ``" -ForegroundColor White
    Write-Host "    semitechnologies/weaviate:latest" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Success "Weaviate is running"
Write-Host ""

# Execute command
switch ($Command) {
    'init'   { Initialize-Collections }
    'test'   { Run-Tests }
    'ingest' { Invoke-Ingestion }
    'stats'  { Show-Statistics }
    'search' { Search-Sections }
    'verify' { Verify-File }
    'help'   { Show-Help }
    default  { Show-Help }
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
