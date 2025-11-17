#!/bin/bash
# Quick start script for AODA Compliance Checker with MySQL

set -e

echo "🚀 AODA Compliance Checker - Docker Quick Start"
echo "================================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker compose is available (V2 syntax)
if ! docker compose version > /dev/null 2>&1; then
    echo "❌ Docker Compose is not available. Please install Docker Compose V2."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Stop existing containers if any
echo "🛑 Stopping existing containers (if any)..."
docker compose down > /dev/null 2>&1 || true
echo ""

# Build and start services
echo "🏗️  Building application image..."
docker compose build --no-cache

echo ""
echo "🚀 Starting services..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."

# Wait for MySQL to be healthy
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker inspect aoda-mysql | grep -q '"Status": "healthy"'; then
        echo "✅ MySQL is healthy"
        break
    fi
    attempt=$((attempt + 1))
    echo "Waiting for MySQL... ($attempt/$max_attempts)"
    sleep 2
done

# Wait for application to be healthy
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker inspect aoda-compliance-checker | grep -q '"Status": "healthy"'; then
        echo "✅ Application is healthy"
        break
    fi
    attempt=$((attempt + 1))
    echo "Waiting for application... ($attempt/$max_attempts)"
    sleep 2
done

echo ""
echo "================================================"
echo "✅ AODA Compliance Checker is ready!"
echo "================================================"
echo ""
echo "📍 Web interface: http://localhost:8080"
echo "📊 Database: MySQL 8.4 on port 3306"
echo ""
echo "Useful commands:"
echo "  View logs:        docker compose logs -f"
echo "  Stop services:    docker compose down"
echo "  Restart:          docker compose restart"
echo "  Access MySQL:     docker compose exec mysql mysql -u aoda_user -paoda_password aoda_checker"
echo ""
echo "📚 Documentation: docs/MYSQL_GUIDE.md"
echo ""

