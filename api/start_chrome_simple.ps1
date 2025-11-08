# Simple command to start Chrome with remote debugging
# Close ALL Chrome windows first, then run this:

Write-Host "Starting Chrome with remote debugging..." -ForegroundColor Green

# Find Chrome
$chromePath = $null
$paths = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

foreach ($path in $paths) {
    if (Test-Path $path) {
        $chromePath = $path
        break
    }
}

if ($chromePath) {
    # Kill any existing Chrome processes
    Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    
    # Start Chrome with remote debugging
    Start-Process -FilePath $chromePath -ArgumentList "--remote-debugging-port=9222"
    
    Write-Host "Chrome started with remote debugging on port 9222!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Log into LinkedIn at https://www.linkedin.com" -ForegroundColor White
    Write-Host "2. Keep Chrome running" -ForegroundColor White
    Write-Host "3. Use your website - it will now connect to Chrome" -ForegroundColor White
} else {
    Write-Host "ERROR: Chrome not found!" -ForegroundColor Red
}

