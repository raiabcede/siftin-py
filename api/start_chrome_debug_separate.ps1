# Start Chrome with Remote Debugging WITHOUT closing existing Chrome
# This uses a separate user data directory so both can run simultaneously

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Chrome with Remote Debugging (Separate Instance)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

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
# This allows it to run alongside your existing Chrome
$debugDir = "$env:TEMP\chrome_debug_linkedin"
New-Item -ItemType Directory -Force -Path $debugDir | Out-Null

Write-Host "Starting Chrome with remote debugging on port 9222..." -ForegroundColor Green
Write-Host "Using separate user data directory: $debugDir" -ForegroundColor Yellow
Write-Host "This allows it to run alongside your existing Chrome instance." -ForegroundColor Yellow
Write-Host ""

# Start Chrome with remote debugging using separate user data directory
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
    Write-Host "1. Log into LinkedIn in the NEW Chrome window that opened" -ForegroundColor White
    Write-Host "2. Keep this Chrome window running while using the scraper" -ForegroundColor White
    Write-Host "3. Your original Chrome instance remains untouched" -ForegroundColor White
    Write-Host ""
    Write-Host "IMPORTANT: Keep the Chrome window with remote debugging running!" -ForegroundColor Yellow
    Write-Host "Don't close it while using the scraper." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "WARNING: Port 9222 is not open yet." -ForegroundColor Yellow
    Write-Host "Chrome may need more time to start. Wait a few seconds and try again." -ForegroundColor Yellow
}

Write-Host ""
Read-Host "Press Enter to exit"

