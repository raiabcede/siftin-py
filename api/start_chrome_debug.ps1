# Start Chrome with Remote Debugging for LinkedIn Scraper
# This script starts Chrome with remote debugging enabled on port 9222

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Chrome with Remote Debugging" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Close any existing Chrome instances
Write-Host "Closing existing Chrome windows..." -ForegroundColor Yellow
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Find Chrome executable
$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chromePath)) {
    $chromePath = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
}

if (-not (Test-Path $chromePath)) {
    Write-Host "ERROR: Chrome not found!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Create separate user data directory for remote debugging
$debugDir = "$env:TEMP\chrome_debug"
New-Item -ItemType Directory -Force -Path $debugDir | Out-Null

Write-Host "Starting Chrome with remote debugging on port 9222..." -ForegroundColor Green
Start-Process -FilePath $chromePath -ArgumentList "--remote-debugging-port=9222", "--user-data-dir=$debugDir"

# Wait for Chrome to start
Start-Sleep -Seconds 5

# Verify port is open
$portTest = Test-NetConnection -ComputerName localhost -Port 9222 -InformationLevel Quiet -WarningAction SilentlyContinue

if ($portTest) {
    Write-Host ""
    Write-Host "SUCCESS! Chrome is running with remote debugging!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Log into LinkedIn at https://www.linkedin.com" -ForegroundColor White
    Write-Host "2. Keep Chrome running while using your website" -ForegroundColor White
    Write-Host "3. The scraper will automatically connect to this Chrome session" -ForegroundColor White
    Write-Host ""
    Write-Host "IMPORTANT: Keep Chrome running. Don't close it!" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "WARNING: Port 9222 is not open yet." -ForegroundColor Yellow
    Write-Host "Chrome may need more time to start. Wait a few seconds and try again." -ForegroundColor Yellow
}

Write-Host ""
Read-Host "Press Enter to exit"
