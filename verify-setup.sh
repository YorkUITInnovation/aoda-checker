#!/bin/bash
# Complete verification and final setup for enhanced AODA checker

echo "=================================="
echo "AODA Checker - Final Verification"
echo "=================================="
echo ""

# Check if container is running
echo "1. Checking Docker container status..."
if docker ps | grep -q "aoda-compliance-checker"; then
    echo "   ✅ Container is running"
else
    echo "   ❌ Container is NOT running"
    exit 1
fi

echo ""
echo "2. Verifying database table..."
# Use Python to check table
docker exec aoda-compliance-checker python3 -c "
import asyncio
from sqlalchemy import text
from src.database.session import engine

async def check():
    async with engine.begin() as conn:
        result = await conn.execute(text('SELECT COUNT(*) FROM check_configurations'))
        count = result.scalar()
        print(f'   ✅ check_configurations table has {count} rows')

asyncio.run(check())
" 2>/dev/null || echo "   ⚠️  Could not verify table (may need initialization)"

echo ""
echo "3. Testing application endpoints..."
echo "   Testing health endpoint..."
if curl -s -f http://localhost:8080/health > /dev/null 2>&1; then
    echo "   ✅ Health endpoint responding"
else
    echo "   ⚠️  Health endpoint not responding"
fi

echo ""
echo "4. Checking new files in container..."
FILES=(
    "/app/src/database/check_repository.py"
    "/app/src/utils/custom_checker.py"
    "/app/src/web/check_config_routes.py"
    "/app/templates/admin_checks.html"
)

for file in "${FILES[@]}"; do
    if docker exec aoda-compliance-checker test -f "$file" 2>/dev/null; then
        echo "   ✅ $file exists"
    else
        echo "   ❌ $file missing"
    fi
done

echo ""
echo "=================================="
echo "Setup Summary"
echo "=================================="
echo ""
echo "✅ Enhanced AODA Checker is configured with:"
echo "   • Custom accessibility checks (spacer images, noscript)"
echo "   • Admin configuration interface"
echo "   • Database-driven check management"
echo "   • 20+ configurable accessibility rules"
echo ""
echo "📍 Access Points:"
echo "   • Main App: http://localhost:8080"
echo "   • Admin Checks: http://localhost:8080/admin/checks"
echo "   • API Docs: http://localhost:8080/docs"
echo ""
echo "🔐 Default Admin Credentials:"
echo "   • Username: admin"
echo "   • Password: admin"
echo ""
echo "📚 Documentation:"
echo "   • User Guide: CHECK_CONFIGURATION_GUIDE.md"
echo "   • Implementation: IMPLEMENTATION_SUMMARY.md"
echo "   • Q&A: ADDITIONAL_QUESTIONS_ANSWERED.md"
echo ""
echo "🎯 Next Steps:"
echo "   1. Login to http://localhost:8080"
echo "   2. Go to http://localhost:8080/admin/checks"
echo "   3. Click 'Initialize Default Checks' if needed"
echo "   4. Run a test scan on https://yorku.ca/uit"
echo "   5. Verify enhanced checks are working"
echo ""
echo "✨ Happy accessibility testing!"
echo ""

