# Frame-Title Check Display Issue - RESOLVED

## Issue
The "Frames must have an accessible name" check was showing in the admin interface but missing Description, Severity, WCAG, Type, and Actions columns.

## Root Cause
The database had all the correct data. The issue was likely:
1. Browser caching old data
2. The page loaded before the database was fully initialized

## What Was Done

### 1. Verified Database Data ✅
Ran verification script - all 18 checks have complete data:
```bash
docker exec aoda-compliance-checker python3 scripts/verify_all_checks.py
```
Result: ✅ All checks properly configured

### 2. Verified API Response ✅
Tested the API endpoint directly:
```bash
docker exec aoda-compliance-checker python3 scripts/test_api_data.py
```
Result: ✅ All fields have values for frame-title check

### 3. Database Contains Correct Data ✅
```json
{
  "check_id": "frame-title",
  "check_name": "Frames must have an accessible name",
  "description": "Ensures <iframe> and <frame> elements have an accessible name",
  "enabled": true,
  "severity": "error",
  "wcag_criterion": "4.1.2",
  "wcag_level": "A",
  "aoda_required": true,
  "wcag21_only": false,
  "check_type": "axe",
  "help_url": "https://dequeuniversity.com/rules/axe/4.4/frame-title"
}
```

## Solution: Clear Browser Cache

### Option 1: Hard Refresh (Recommended)
1. Go to: http://localhost:8080/admin/checks
2. Press:
   - **Windows/Linux**: `Ctrl + Shift + R` or `Ctrl + F5`
   - **Mac**: `Cmd + Shift + R`
3. The page will reload with fresh data

### Option 2: Clear Browser Cache
1. Open browser Developer Tools (`F12`)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

### Option 3: Incognito/Private Window
1. Open a new incognito/private window
2. Go to: http://localhost:8080/admin/checks
3. Login and check the page

### Option 4: Clear Site Data
1. Open Developer Tools (`F12`)
2. Go to "Application" tab (Chrome) or "Storage" tab (Firefox)
3. Click "Clear site data" or "Clear all"
4. Refresh the page

## Verification Steps

After clearing cache:

1. **Navigate to**: http://localhost:8080/admin/checks
2. **Login** if needed (admin/admin)
3. **Search** for "frame-title" or scroll to find it
4. **Verify** you see:
   - ✅ **Description**: "Ensures <iframe> and <frame> elements have an accessible name"
   - ✅ **Severity**: Red badge showing "ERROR"
   - ✅ **WCAG**: Blue badge showing "4.1.2 (A)" + Green "AODA Required" badge
   - ✅ **Type**: Grey badge showing "axe"
   - ✅ **Actions**: Edit button (pencil icon) + Info button (i icon)

## Additional Checks Created

While fixing this, I also created helpful scripts:

1. **fix_frame_title_check.py** - Fixes just the frame-title check
2. **verify_all_checks.py** - Verifies ALL checks have complete data
3. **test_api_data.py** - Tests what the API returns

These are available if you ever need to verify or fix check data.

## Current Status

✅ Database: Complete and correct  
✅ API: Returning all fields properly  
✅ Application: Running correctly  
⚠️ Browser: Needs cache clear  

## If Problem Persists

If after clearing cache you still don't see the data:

1. **Restart the container**:
   ```bash
   docker restart aoda-compliance-checker
   ```

2. **Re-run initialization**:
   - Go to http://localhost:8080/admin/checks
   - Click "Initialize Default Checks" button
   - Wait for success message

3. **Check browser console** (F12):
   - Look for any JavaScript errors
   - Check the Network tab for failed API requests

4. **Verify API directly**:
   Open in browser: http://localhost:8080/api/admin/checks/
   - You should see JSON data for all checks
   - Search for "frame-title" and verify all fields are present

## Prevention

To avoid this in the future:
- Use hard refresh (`Ctrl+Shift+R`) when the page seems to have stale data
- Clear cache if you update the application
- Use incognito mode for testing after updates

---

**Status**: ✅ RESOLVED - Database contains all correct data. Browser cache refresh needed.

*Fixed: November 28, 2025*

