# AODA Scan Mode Feature - Deployment Checklist

## ✅ Pre-Deployment Checklist

### Code Changes Complete
- [x] Created AODA requirements module (`src/utils/aoda_requirements.py`)
- [x] Added ScanMode enum to models
- [x] Updated ScanRequest and ScanResult models
- [x] Modified crawler to use scan mode configuration
- [x] Added scan_mode column to database models
- [x] Updated repository to handle scan_mode
- [x] Created database migration script
- [x] Updated scan form UI with mode selection
- [x] Updated results page to show scan mode
- [x] Updated history page to display scan mode
- [x] Updated README with new feature

### Code Verification
- [x] All Python files compile without syntax errors
- [x] Models updated correctly
- [x] Database schema changes defined
- [x] UI templates updated

## 🚀 Deployment Steps

### Step 1: Rebuild Docker Container
```bash
# Stop the current container
docker compose down

# Rebuild with new changes
docker compose up -d --build

# Verify container is running
docker compose ps
```

### Step 2: Run Database Migration
```bash
# Execute migration script inside container
docker exec -it aoda-compliance-checker python scripts/add_scan_mode_column.py

# Expected output:
# ============================================================
# Database Migration: Add scan_mode Column
# ============================================================
# Adding 'scan_mode' column to 'scans' table...
# ✓ Successfully added 'scan_mode' column to 'scans' table
#   Default value: 'aoda'
# 
# ✓ Migration completed successfully!
```

### Step 3: Verify Deployment
```bash
# Check application logs
docker compose logs -f aoda-compliance-checker

# Look for startup messages like:
# "Database initialized successfully"
# "Application startup complete"
```

### Step 4: Test the Feature
1. Access the application at http://localhost:8080
2. Log in with your credentials
3. Go to the scan form (homepage)
4. Verify the "Accessibility Standard" dropdown is present
5. Try scanning with AODA mode (default)
6. Try scanning with WCAG 2.1 mode
7. Check results page shows the scan mode
8. Verify history page displays scan mode for each scan

## 🧪 Testing Scenarios

### Test 1: AODA Mode Scan
1. Select "Ontario AODA/IASR (WCAG 2.0 Level AA)"
2. Enter a URL (e.g., https://yorku.ca/uit)
3. Start scan
4. Verify results page shows "Ontario AODA/IASR (WCAG 2.0 Level AA)"
5. Check that scan appears in history with "Ontario AODA" label

### Test 2: WCAG 2.1 Mode Scan
1. Select "Full WCAG 2.1 Level AA"
2. Enter the same URL
3. Start scan
4. Verify results page shows "WCAG 2.1 Level AA"
5. Check that scan appears in history with "WCAG 2.1" label
6. Compare number of violations with AODA scan (may be higher)

### Test 3: Backward Compatibility
1. Check existing scans in history
2. Verify they default to "Ontario AODA" if no mode was set
3. Ensure old scans still display correctly

## 📊 Expected Behavior

### Scan Form
- Dropdown labeled "Accessibility Standard"
- Two options:
  - "Ontario AODA/IASR (WCAG 2.0 Level AA)" (selected by default)
  - "Full WCAG 2.1 Level AA"
- Help text explaining the difference

### Results Page
- Header section shows scan mode used:
  - "Ontario AODA/IASR (WCAG 2.0 Level AA)" or
  - "WCAG 2.1 Level AA"

### History Page
- Each scan card shows:
  - Scan mode (Ontario AODA or WCAG 2.1)
  - Max pages and max depth
  - Number of pages and violations

## 🔍 Troubleshooting

### Issue: Migration script fails
**Solution:**
```bash
# Check if column already exists
docker exec -it aoda-compliance-checker mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "DESCRIBE aoda_checker.scans;"

# If column exists, migration is already complete
```

### Issue: Scan mode not showing in UI
**Solution:**
1. Clear browser cache
2. Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
3. Verify JavaScript console for errors

### Issue: Scans fail with new mode
**Solution:**
1. Check application logs: `docker compose logs -f`
2. Verify axe-playwright-python is installed in container
3. Ensure scan_mode is being passed correctly

## 📝 Rollback Plan (if needed)

If you need to revert changes:

```bash
# Remove the scan_mode column
docker exec -it aoda-compliance-checker mysql -uroot -p${MYSQL_ROOT_PASSWORD} -e "ALTER TABLE aoda_checker.scans DROP COLUMN scan_mode;"

# Rebuild from previous Docker image
docker compose down
git checkout <previous-commit>
docker compose up -d --build
```

## ✨ Success Criteria

- [ ] Docker container builds successfully
- [ ] Database migration runs without errors
- [ ] Scan form displays mode selection dropdown
- [ ] AODA scans complete successfully
- [ ] WCAG 2.1 scans complete successfully
- [ ] Results page shows correct scan mode
- [ ] History page displays scan mode for all scans
- [ ] No errors in application logs
- [ ] No JavaScript errors in browser console

## 📚 Documentation

Additional documentation created:
- `AODA_SCAN_MODE_FEATURE.md` - Technical implementation details
- `README.md` - Updated with new feature
- This checklist for deployment

## 🎯 Next Steps After Deployment

1. **Monitor Performance**: Track scan times for both modes
2. **Gather Feedback**: Ask users about the feature
3. **Compare Results**: Analyze differences between scan modes
4. **Documentation**: Create user guide for choosing scan modes
5. **Training**: Educate team on when to use each mode

---

**Ready to deploy!** Follow the steps above to implement the AODA scan mode feature.

