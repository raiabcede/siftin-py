# Quick test to verify Chrome remote debugging is working
Write-Host "Testing Chrome Remote Debugging Connection..." -ForegroundColor Cyan
Write-Host ""

# Check if port 9222 is open
$portTest = Test-NetConnection -ComputerName localhost -Port 9222 -InformationLevel Quiet -WarningAction SilentlyContinue

if ($portTest) {
    Write-Host "✓ Port 9222 is OPEN - Remote debugging is active!" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now use your website to scrape LinkedIn." -ForegroundColor Green
    Write-Host ""
    Write-Host "Make sure:" -ForegroundColor Yellow
    Write-Host "  1. Chrome is running (started with remote debugging)" -ForegroundColor White
    Write-Host "  2. You are logged into LinkedIn in Chrome" -ForegroundColor White
    Write-Host "  3. Keep Chrome running while using the scraper" -ForegroundColor White
} else {
    Write-Host "✗ Port 9222 is CLOSED - Remote debugging is NOT active" -ForegroundColor Red
    Write-Host ""
    Write-Host "To fix this:" -ForegroundColor Yellow
    Write-Host "  1. Close ALL Chrome windows completely" -ForegroundColor White
    Write-Host "  2. Run: .\start_chrome_debug.ps1" -ForegroundColor White
    Write-Host "  3. Log into LinkedIn in the Chrome window that opens" -ForegroundColor White
    Write-Host "  4. Keep Chrome running" -ForegroundColor White
}

Write-Host ""
Read-Host "Press Enter to exit"

