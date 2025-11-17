#!/bin/bash
# Quick start script for Docker version

echo "🐳 AODA Compliance Checker - Docker Quick Start"
echo "================================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "   Please start Docker Desktop and try again."
    exit 1
fi

echo "✓ Docker is running"
echo ""

cd "$(dirname "$0")"

echo "Building and starting the container..."
echo "(This may take a few minutes on first run)"
echo ""

docker compose up --build -d

if [ $? -eq 0 ]; then
    echo ""
    echo "================================================"
    echo "✅ AODA Compliance Checker is running!"
    echo "================================================"
    echo ""
    echo "🌐 Open in browser: http://localhost:8080"
    echo ""
    echo "📊 Useful commands:"
    echo "   View logs:    docker compose logs -f"
    echo "   Stop server:  docker compose down"
    echo "   Restart:      docker compose restart"
    echo ""
    echo "Waiting for server to be ready..."
    sleep 5

    # Check health
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "✅ Server is healthy and ready!"
        echo ""
        echo "🚀 Opening browser..."
        open http://localhost:8080 2>/dev/null || echo "   Please open: http://localhost:8080"
    else
        echo "⏳ Server is starting... check logs with: docker compose logs -f"
    fi
else
    echo ""
    echo "❌ Failed to start. Check the error messages above."
    echo "   Try: docker compose logs"
fi

