#!/bin/bash
# Quick verification script for history page fix

echo "=========================================="
echo "History Page Fix Verification"
echo "=========================================="
echo

# Check if containers are running
echo "1. Checking Docker containers..."
if docker ps | grep -q "aoda-compliance-checker"; then
    echo "   ✓ Application container is running"
else
    echo "   ✗ Application container is NOT running"
    echo "   Starting containers..."
    cd /projects/aoda-checker
    docker compose up -d
    sleep 5
fi

if docker ps | grep -q "aoda-mysql"; then
    echo "   ✓ MySQL container is running"
else
    echo "   ✗ MySQL container is NOT running"
    exit 1
fi

echo

# Check if scan_mode column exists
echo "2. Checking database schema..."
COLUMN_EXISTS=$(docker exec aoda-mysql mysql -uroot -paoda2024 -se "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='aoda_checker' AND TABLE_NAME='scans' AND COLUMN_NAME='scan_mode';" 2>/dev/null)

if [ "$COLUMN_EXISTS" = "1" ]; then
    echo "   ✓ scan_mode column exists in database"
else
    echo "   ✗ scan_mode column does NOT exist"
    echo "   Running migration..."
    docker exec aoda-compliance-checker python scripts/add_scan_mode_column.py
    echo
fi

echo

# Check if there are any scans
echo "3. Checking for existing scans..."
SCAN_COUNT=$(docker exec aoda-mysql mysql -uroot -paoda2024 -se "SELECT COUNT(*) FROM aoda_checker.scans;" 2>/dev/null)

if [ -n "$SCAN_COUNT" ] && [ "$SCAN_COUNT" -gt 0 ]; then
    echo "   ✓ Found $SCAN_COUNT scan(s) in database"

    echo
    echo "4. Sample scan data:"
    docker exec aoda-mysql mysql -uroot -paoda2024 -e "SELECT scan_id, LEFT(start_url, 50) as url, scan_mode, status FROM aoda_checker.scans LIMIT 3;" 2>/dev/null
else
    echo "   ⚠ No scans found in database"
    echo "   History page will be empty (this is normal for new installations)"
fi

echo
echo "5. Restarting application to load changes..."
docker compose restart aoda-compliance-checker > /dev/null 2>&1
sleep 3
echo "   ✓ Application restarted"

echo
echo "=========================================="
echo "Verification Complete!"
echo "=========================================="
echo
echo "Next steps:"
echo "1. Open http://localhost:8080 in your browser"
echo "2. Log in"
echo "3. Go to History page"
echo "4. The page should load without errors"
echo
echo "If you still see errors:"
echo "- Check browser console (F12) for details"
echo "- Review logs: docker compose logs aoda-compliance-checker"
echo "- See HISTORY_PAGE_TROUBLESHOOTING.md for more help"
echo

