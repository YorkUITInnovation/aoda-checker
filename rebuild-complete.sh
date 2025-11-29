#!/bin/bash
# Complete rebuild and restart script for AODA Checker

echo "🔨 AODA Checker - Complete Rebuild"
echo "==================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "This will:"
echo "  1. Rebuild the Docker image from scratch (includes all new files)"
echo "  2. Restart the container with the new image"
echo "  3. Verify the application is running"
echo ""

# Step 1: Stop the current container
echo "📦 Step 1: Stopping current container..."
docker stop aoda-compliance-checker 2>/dev/null || true
echo -e "${GREEN}✅ Container stopped${NC}"
echo ""

# Step 2: Rebuild the image (no cache)
echo "🔨 Step 2: Rebuilding Docker image (this may take 5-10 minutes)..."
echo "   This includes ALL new files:"
echo "     - src/database/check_repository.py"
echo "     - src/database/models.py (updated)"
echo "     - src/utils/custom_checker.py"
echo "     - src/web/check_config_routes.py"
echo "     - templates/admin_checks.html (updated with logging)"
echo "     - All scripts and documentation"
echo ""

if docker compose build --no-cache aoda-checker; then
    echo -e "${GREEN}✅ Image rebuilt successfully${NC}"
else
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi

echo ""

# Step 3: Start the container
echo "🚀 Step 3: Starting container with new image..."
docker compose up -d aoda-checker

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Container started${NC}"
else
    echo -e "${RED}❌ Failed to start container${NC}"
    exit 1
fi

echo ""

# Step 4: Wait for application to be ready
echo "⏳ Step 4: Waiting for application to be ready..."
sleep 10

# Check if container is running
if docker ps | grep -q "aoda-compliance-checker"; then
    echo -e "${GREEN}✅ Container is running${NC}"
else
    echo -e "${RED}❌ Container is not running${NC}"
    exit 1
fi

echo ""

# Step 5: Verify the application
echo "🔍 Step 5: Verifying application..."

# Check health endpoint
if curl -s -f http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Application is responding${NC}"
else
    echo -e "${YELLOW}⚠️  Application not responding yet (may need more time)${NC}"
fi

echo ""

# Step 6: Verify new files are in the container
echo "📂 Step 6: Verifying new files are present in container..."

FILES_TO_CHECK=(
    "/app/src/database/check_repository.py"
    "/app/src/utils/custom_checker.py"
    "/app/src/web/check_config_routes.py"
    "/app/templates/admin_checks.html"
    "/app/scripts/debug_checks.py"
    "/app/scripts/verify_all_checks.py"
    "/app/static/diagnostic.html"
)

ALL_FILES_PRESENT=true
for file in "${FILES_TO_CHECK[@]}"; do
    if docker exec aoda-compliance-checker test -f "$file" 2>/dev/null; then
        echo -e "  ${GREEN}✅${NC} $file"
    else
        echo -e "  ${RED}❌${NC} $file"
        ALL_FILES_PRESENT=false
    fi
done

echo ""

if [ "$ALL_FILES_PRESENT" = true ]; then
    echo -e "${GREEN}✅ All new files are present in the container${NC}"
else
    echo -e "${YELLOW}⚠️  Some files are missing${NC}"
fi

echo ""

# Step 7: Verify database table
echo "🗄️  Step 7: Verifying check_configurations table..."
docker exec aoda-compliance-checker python3 -c "
import asyncio
from src.database.check_repository import CheckConfigRepository
from src.database import get_db_session

async def check():
    async with get_db_session() as db:
        repo = CheckConfigRepository(db)
        checks = await repo.get_all_checks()
        print(f'Table has {len(checks)} checks')
        return len(checks)

count = asyncio.run(check())
" 2>/dev/null

echo ""

# Final summary
echo "==================================="
echo -e "${GREEN}🎉 Rebuild Complete!${NC}"
echo "==================================="
echo ""
echo "Next steps:"
echo "  1. Open: http://localhost:8080"
echo "  2. Login: admin / admin"
echo "  3. Go to: http://localhost:8080/admin/checks"
echo "  4. Verify all 18 checks are showing"
echo "  5. If table is empty, click 'Initialize Default Checks'"
echo ""
echo "Diagnostic URLs:"
echo "  • Admin Checks: http://localhost:8080/admin/checks"
echo "  • Diagnostic: http://localhost:8080/static/diagnostic.html"
echo "  • API: http://localhost:8080/api/admin/checks/"
echo ""
echo "View logs: docker logs aoda-compliance-checker"
echo ""

