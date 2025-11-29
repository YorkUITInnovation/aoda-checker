#!/bin/bash
# Test the API endpoint to see how many checks it returns

echo "Testing API endpoint: /api/admin/checks/"
echo "=========================================="
echo ""

# Get a session cookie by logging in first
echo "1. Logging in..."
LOGIN_RESPONSE=$(curl -s -c /tmp/cookies.txt -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin")

if echo "$LOGIN_RESPONSE" | grep -q "success\|token"; then
    echo "   ✅ Login successful"
else
    echo "   ❌ Login failed"
    echo "   Response: $LOGIN_RESPONSE"
    exit 1
fi

echo ""
echo "2. Fetching checks from API..."
API_RESPONSE=$(curl -s -b /tmp/cookies.txt http://localhost:8080/api/admin/checks/)

# Count how many checks were returned
CHECK_COUNT=$(echo "$API_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data))" 2>/dev/null)

if [ -z "$CHECK_COUNT" ]; then
    echo "   ❌ Failed to parse API response"
    echo "   Response: $API_RESPONSE" | head -20
    exit 1
fi

echo "   ✅ API returned $CHECK_COUNT checks"
echo ""

echo "3. List of check IDs returned:"
echo "$API_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for i, check in enumerate(data, 1):
    print(f'   {i:2d}. {check[\"check_id\"]}')
" 2>/dev/null

echo ""
echo "=========================================="
echo "Summary: API returns $CHECK_COUNT out of 18 checks"
echo "=========================================="

