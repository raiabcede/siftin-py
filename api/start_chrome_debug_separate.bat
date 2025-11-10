@echo off
echo Starting Chrome with Remote Debugging (Separate Instance)
echo This uses a separate user data directory so it can run alongside your existing Chrome.
echo.

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

REM Create separate user data directory
set DEBUG_DIR=%TEMP%\chrome_debug_linkedin
if not exist "%DEBUG_DIR%" mkdir "%DEBUG_DIR%"

echo Starting Chrome with remote debugging on port 9222...
echo Using separate user data directory: %DEBUG_DIR%
echo This allows it to run alongside your existing Chrome instance.
echo.

"%CHROME_PATH%" --remote-debugging-port=9222 --user-data-dir="%DEBUG_DIR%"

echo.
echo Chrome is now running with remote debugging enabled.
echo You can now log into LinkedIn in the NEW Chrome window that opened.
echo Keep this window running while using the scraper.
echo Your original Chrome instance remains untouched.
echo.
pause

