#!/bin/bash

# Start the AODA Compliance Checker web interface
# This script sets up the proper environment for WeasyPrint

echo "🚀 Starting AODA Compliance Checker..."

# Set library paths for WeasyPrint on macOS
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"

# Activate virtual environment if not already activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    source .venv/bin/activate
fi

# Start the web server
python main.py web "$@"

