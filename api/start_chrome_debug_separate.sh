#!/bin/bash

echo "Starting Chrome with Remote Debugging (Separate Instance)"
echo "This uses a separate user data directory so it can run alongside your existing Chrome."
echo ""

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

# Create separate user data directory
DEBUG_DIR="$HOME/.chrome_debug_linkedin"
mkdir -p "$DEBUG_DIR"

echo "Starting Chrome with remote debugging on port 9222..."
echo "Using separate user data directory: $DEBUG_DIR"
echo "This allows it to run alongside your existing Chrome instance."
echo ""

"$CHROME_PATH" --remote-debugging-port=9222 --user-data-dir="$DEBUG_DIR" &

echo ""
echo "Chrome is now running with remote debugging enabled."
echo "You can now log into LinkedIn in the NEW Chrome window that opened."
echo "Keep this window running while using the scraper."
echo "Your original Chrome instance remains untouched."
echo ""

