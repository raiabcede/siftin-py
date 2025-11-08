# FastAPI Server Startup Script
Write-Host "Starting FastAPI server..." -ForegroundColor Green
Write-Host ""

# Change to the script's directory
Set-Location $PSScriptRoot

# Check if Python is available
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from https://www.python.org/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if FastAPI is installed
Write-Host "Checking dependencies..." -ForegroundColor Yellow
try {
    python -c "import fastapi" 2>&1 | Out-Null
    Write-Host "✓ Dependencies are installed" -ForegroundColor Green
} catch {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host ""
Write-Host "Starting FastAPI server on http://localhost:8000" -ForegroundColor Green
Write-Host "Press CTRL+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Run the server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

