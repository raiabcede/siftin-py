@echo off
echo Starting Chrome with remote debugging enabled...
echo This allows the scraper to connect to your existing Chrome session.
echo.
echo IMPORTANT: Close ALL Chrome windows first, then run this script.
echo.
pause

REM Find Chrome executable
set CHROME_PATH=
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
) else (
    echo Chrome not found in default locations.
    echo Please edit this script and add the path to chrome.exe
    pause
    exit /b 1
)

echo Starting Chrome with remote debugging on port 9222...
"%CHROME_PATH%" --remote-debugging-port=9222

echo.
echo Chrome is now running with remote debugging enabled.
echo You can now log into LinkedIn in Chrome, then run the scraper.
echo Keep this window open while using the scraper.
echo.
pause

