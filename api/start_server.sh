#!/bin/bash

echo "Starting FastAPI server..."
echo ""
echo "Make sure you have:"
echo "  1. Python 3.8+ installed"
echo "  2. Dependencies installed: pip install -r requirements.txt"
echo "  3. Chrome browser installed (for scraping)"
echo ""
echo "Server will start on http://localhost:8000"
echo ""

cd "$(dirname "$0")"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ from https://www.python.org/"
    exit 1
fi

# Check if requirements are installed
python3 -c "import fastapi" &> /dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies"
        exit 1
    fi
fi

echo "Starting FastAPI server..."
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

