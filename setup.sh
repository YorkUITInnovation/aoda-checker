#!/bin/bash

# AODA Compliance Checker - Quick Start Script

echo "🔍 AODA Compliance Checker Setup"
echo "================================"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "🌐 Installing Playwright Chromium browser (this may take a moment)..."
playwright install chromium

# Create necessary directories
mkdir -p reports static templates

echo ""
echo "✅ Setup complete!"
echo ""
echo "⚠️  Note: If you see 'Scan failed' errors, run: playwright install chromium"
echo ""
echo "Usage:"
echo "------"
echo "1. Web Interface:"
echo "   python main.py web"
echo "   Then open http://localhost:8000"
echo ""
echo "2. Command Line:"
echo "   python main.py scan --url https://example.com --max-pages 10"
echo ""
echo "For help:"
echo "   python main.py --help"
echo ""

