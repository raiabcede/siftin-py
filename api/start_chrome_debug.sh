#!/bin/bash

echo "Starting Chrome with remote debugging enabled..."
echo "This allows the scraper to connect to your existing Chrome session."
echo ""
echo "IMPORTANT: Close ALL Chrome windows first, then run this script."
echo ""
read -p "Press Enter to continue..."

# Find Chrome executable based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    CHROME_PATH=$(which google-chrome || which chromium-browser || which chrome)
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi

if [ ! -f "$CHROME_PATH" ]; then
    echo "Chrome not found. Please install Google Chrome."
    exit 1
fi

echo "Starting Chrome with remote debugging on port 9222..."
"$CHROME_PATH" --remote-debugging-port=9222 &

echo ""
echo "Chrome is now running with remote debugging enabled."
echo "You can now log into LinkedIn in Chrome, then run the scraper."
echo "Keep this terminal open while using the scraper."
echo ""
read -p "Press Enter to exit..."

