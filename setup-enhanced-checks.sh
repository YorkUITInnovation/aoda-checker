#!/bin/bash
# Setup script for enhanced AODA checker with check configuration

echo "🚀 AODA Checker - Enhanced Check Configuration Setup"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Rebuild Docker image
echo "📦 Step 1: Rebuilding Docker image with new code..."
docker-compose build aoda-checker
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker image built successfully${NC}"
else
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

echo ""

# Step 2: Restart container
echo "🔄 Step 2: Restarting Docker container..."
docker-compose up -d
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Container restarted${NC}"
else
    echo -e "${RED}❌ Container restart failed${NC}"
    exit 1
fi

echo ""
echo "⏳ Waiting for application to start..."
sleep 10

# Step 3: Run migration
echo "🗄️  Step 3: Creating check_configurations table..."
docker exec aoda-compliance-checker python3 scripts/add_check_configurations_table.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database migration completed${NC}"
else
    echo -e "${YELLOW}⚠️  Migration may have already run or encountered an issue${NC}"
fi

echo ""

# Step 4: Verify table exists
echo "🔍 Step 4: Verifying database table..."
TABLE_EXISTS=$(docker exec aoda-mysql mysql -uroot -proot_password_change_in_production -e "USE aoda_checker; SHOW TABLES LIKE 'check_configurations';" 2>/dev/null | grep -c "check_configurations")

if [ "$TABLE_EXISTS" -gt 0 ]; then
    echo -e "${GREEN}✅ check_configurations table exists${NC}"

    # Count checks
    CHECK_COUNT=$(docker exec aoda-mysql mysql -uroot -proot_password_change_in_production -e "USE aoda_checker; SELECT COUNT(*) FROM check_configurations;" 2>/dev/null | tail -1)
    echo -e "${GREEN}📊 Number of checks configured: $CHECK_COUNT${NC}"
else
    echo -e "${YELLOW}⚠️  Table verification inconclusive - may need manual check${NC}"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Open your browser to: http://localhost:8080"
echo "  2. Login as admin"
echo "  3. Navigate to: http://localhost:8080/admin/checks"
echo "  4. Click 'Initialize Default Checks' if table is empty"
echo "  5. Configure individual checks as needed"
echo ""
echo "To test the enhancements:"
echo "  - Run a scan on: https://yorku.ca/uit"
echo "  - Compare results with external checkers"
echo "  - You should now see spacer images, empty headings, and noscript checks"
echo ""
echo "Documentation:"
echo "  - User Guide: CHECK_CONFIGURATION_GUIDE.md"
echo "  - Summary: IMPLEMENTATION_SUMMARY.md"
echo ""

