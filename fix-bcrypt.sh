#!/bin/bash
# Quick fix for bcrypt password error and missing dependencies

set -e

echo "════════════════════════════════════════════════════════════"
echo "🔧 Fixing Authentication Dependencies"
echo "════════════════════════════════════════════════════════════"
echo ""

echo "📋 This will:"
echo "   1. Stop the current containers"
echo "   2. Rebuild with all required dependencies"
echo "   3. Start the application"
echo "   4. Show you the logs"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "🛑 Step 1/4: Stopping containers..."
docker compose down
echo "✅ Containers stopped"
echo ""

echo "🏗️  Step 2/4: Rebuilding with fixed dependencies (no cache)..."
docker compose build --no-cache
echo "✅ Rebuild complete"
echo ""

echo "🚀 Step 3/4: Starting containers..."
docker compose up -d
echo "✅ Containers started"
echo ""

echo "⏳ Waiting 10 seconds for initialization..."
sleep 10
echo ""

echo "📊 Step 4/4: Checking status..."
docker compose ps
echo ""

echo "════════════════════════════════════════════════════════════"
echo "📋 Application Logs (last 30 lines):"
echo "════════════════════════════════════════════════════════════"
docker compose logs --tail=30 aoda-checker
echo ""

echo "════════════════════════════════════════════════════════════"
echo "✅ Fix Applied!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "🌐 Access the application:"
echo "   http://localhost:8080/login"
echo ""
echo "🔑 Default credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "⚠️  Change the password after first login!"
echo ""
echo "📝 To view live logs:"
echo "   docker compose logs -f aoda-checker"
echo ""

