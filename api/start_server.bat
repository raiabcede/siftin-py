@echo off
echo Starting FastAPI server...
echo.
echo Make sure you have:
echo   1. Python 3.8+ installed
echo   2. Dependencies installed: pip install -r requirements.txt
echo   3. Chrome browser installed (for scraping)
echo.
echo Server will start on http://localhost:8000
echo.
pause

cd /d %~dp0

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

REM Check if requirements are installed
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo Starting FastAPI server...
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause

