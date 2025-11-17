#!/bin/bash
# Simple Docker rebuild script for AODA Compliance Checker

set -e

echo "════════════════════════════════════════════════════════════"
echo "🔨 AODA Compliance Checker - Docker Rebuild"
echo "════════════════════════════════════════════════════════════"
echo ""

# Stop existing containers
echo "📦 Step 1/5: Stopping existing containers..."
docker compose down
echo "✅ Containers stopped"
echo ""

# Build fresh image (no cache)
echo "🏗️  Step 2/5: Building new Docker image (this may take a few minutes)..."
docker compose build --no-cache
echo "✅ Image built successfully"
echo ""

# Start services
echo "🚀 Step 3/5: Starting services..."
docker compose up -d
echo "✅ Services started"
echo ""

# Wait for services to be healthy
echo "⏳ Step 4/5: Waiting for services to initialize (15 seconds)..."
sleep 15
echo "✅ Initialization complete"
echo ""

# Check status
echo "📊 Step 5/5: Checking service status..."
echo ""
docker compose ps
echo ""

# Show recent logs
echo "════════════════════════════════════════════════════════════"
echo "📋 Recent Application Logs:"
echo "════════════════════════════════════════════════════════════"
docker compose logs --tail=30 aoda-checker
echo ""

# Test health endpoint
echo "════════════════════════════════════════════════════════════"
echo "🏥 Health Check:"
echo "════════════════════════════════════════════════════════════"
if curl -f http://localhost:8080/health 2>/dev/null; then
    echo ""
    echo "✅ Application is healthy!"
else
    echo ""
    echo "⚠️  Health check failed - application may still be starting"
fi
echo ""

echo "════════════════════════════════════════════════════════════"
echo "✨ Build Complete!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📍 Web Interface: http://localhost:8080"
echo "📍 MySQL Database: localhost:3306"
echo "📍 Reports Directory: ./reports/"
echo ""
echo "📝 Useful commands:"
echo "   View logs:         docker compose logs -f aoda-checker"
echo "   Stop services:     docker compose down"
echo "   Restart services:  docker compose restart"
echo ""
echo "════════════════════════════════════════════════════════════"

