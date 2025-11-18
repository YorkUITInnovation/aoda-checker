# History Page Troubleshooting Guide

## Issue
The history page shows: "Failed to load scan history. Please try refreshing the page."

## Root Cause
The `/api/history/scans` endpoint was not returning the `scan_mode` field, and there may have been an issue with how we were checking for the attribute.

## Fixes Applied

### 1. Added scan_mode to API Response
Updated `src/web/history_routes.py` to include `scan_mode` in the scan history response.

Changed from:
```python
"scan_mode": scan.scan_mode if hasattr(scan, 'scan_mode') else 'aoda',
```

To:
```python
"scan_mode": getattr(scan, 'scan_mode', 'aoda'),
```

This is safer and handles missing attributes more gracefully.

### 2. Database Migration
Added the `scan_mode` column to the `scans` table with a default value of 'aoda'.

## How to Fix

### Step 1: Ensure Containers are Running
```bash
cd /projects/aoda-checker
docker compose ps
```

If containers are not running:
```bash
docker compose up -d
```

### Step 2: Run Database Migration
```bash
docker exec aoda-compliance-checker python scripts/add_scan_mode_column.py
```

Expected output:
```
✓ Successfully added 'scan_mode' column to 'scans' table
  Default value: 'aoda'

✓ Migration completed successfully!
```

### Step 3: Restart Application
```bash
docker compose restart aoda-compliance-checker
```

### Step 4: Verify the Fix
1. Open browser to http://localhost:8080
2. Log in
3. Go to History page
4. The page should load without errors

## Verify Database Column Exists
```bash
docker exec aoda-mysql mysql -uroot -paoda2024 -e "SELECT COLUMN_NAME, DATA_TYPE, COLUMN_DEFAULT FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='aoda_checker' AND TABLE_NAME='scans' AND COLUMN_NAME='scan_mode';"
```

Should return:
```
COLUMN_NAME | DATA_TYPE | COLUMN_DEFAULT
scan_mode   | varchar   | aoda
```

## Test API Directly (Advanced)

### Test with curl (requires authentication token):
1. First, get a session by logging in through the browser
2. Then in browser console:
```javascript
fetch('/api/history/scans')
  .then(r => r.json())
  .then(data => console.log(data))
  .catch(err => console.error(err));
```

Expected response:
```json
[
  {
    "scan_id": "...",
    "start_url": "...",
    "status": "completed",
    "pages_scanned": 3,
    "total_violations": 10,
    "max_pages": 50,
    "max_depth": 3,
    "scan_mode": "aoda",
    "start_time": "...",
    "end_time": "...",
    "user_id": 1
  }
]
```

## Common Issues and Solutions

### Issue: "Module not found" error
**Solution:** Rebuild the Docker image
```bash
docker compose down
docker compose up -d --build
```

### Issue: Database connection errors
**Solution:** Check MySQL container health
```bash
docker compose logs aoda-mysql
```

### Issue: Column already exists error
**Solution:** The migration already ran - just restart the app
```bash
docker compose restart aoda-compliance-checker
```

### Issue: Still seeing "Failed to load scan history"
**Solution:** Check browser console for detailed error
1. Open browser DevTools (F12)
2. Go to Console tab
3. Refresh history page
4. Look for error messages
5. Common errors:
   - **401 Unauthorized**: Session expired, log in again
   - **500 Internal Server Error**: Check application logs
   - **Network error**: Container not running

### Issue: Application logs show errors
**Solution:** View detailed logs
```bash
docker compose logs -f aoda-compliance-checker
```

## Verify Everything is Working

### Checklist:
- [ ] Containers are running (`docker compose ps`)
- [ ] Database has scan_mode column
- [ ] Migration completed successfully
- [ ] Application restarted
- [ ] Can log in successfully
- [ ] History page loads without errors
- [ ] Can see scan_mode in scan cards

## Still Having Issues?

### Get Application Logs:
```bash
docker compose logs aoda-compliance-checker --tail=100 > app-logs.txt
```

### Get Browser Console Logs:
1. Open browser DevTools (F12)
2. Go to Console tab
3. Try loading history page
4. Right-click in console → Save as...

### Check Database State:
```bash
docker exec aoda-mysql mysql -uroot -paoda2024 -e "SELECT scan_id, start_url, scan_mode, start_time FROM aoda_checker.scans LIMIT 5;"
```

This will show if scan_mode is properly stored in the database.

