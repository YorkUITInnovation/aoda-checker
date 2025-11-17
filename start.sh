#!/bin/bash
# Simple server startup script

cd /Users/patrickthibaudeau/Documents/aoda_crawler

echo "🚀 Starting AODA Compliance Checker Web Server"
echo "=============================================="
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Run: ./setup.sh"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

echo "✓ Virtual environment activated"
echo ""

# Kill any existing server
pkill -f "python.*uvicorn.*8080" 2>/dev/null
pkill -f "python main.py web" 2>/dev/null
sleep 1

echo "Starting server on http://localhost:8080"
echo ""
echo "⚠️  NOTE: Browser-based scanning won't work due to macOS issues"
echo "   Use: python check_static.py <URL> for working accessibility checks"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=============================================="
echo ""

# Start server
python main.py web --port 8080

