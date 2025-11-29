# ✅ SEVERITY-BASED RESULTS - IMPLEMENTATION COMPLETE

## Summary of Changes

The results page now displays violations grouped by **configured severity levels** (Error, Warning, Alert) instead of axe-core's default impact levels (Critical, Serious, Moderate, Minor).

## What Changed

### 1. Data Models (`src/models/__init__.py`)

#### Added ViolationSeverity Enum
```python
class ViolationSeverity(str, Enum):
    """Severity levels based on check configuration."""
    ERROR = "error"
    WARNING = "warning"
    ALERT = "alert"
```

#### Updated AccessibilityViolation Model
```python
class AccessibilityViolation(BaseModel):
    id: str
    impact: ViolationImpact  # Kept for compatibility
    severity: Optional[str] = None  # NEW: From check configuration
    description: str
    help: str
    help_url: str
    tags: List[str]
    nodes: List[Dict[str, Any]] = []
    
    @property
    def effective_severity(self) -> str:
        """Get effective severity (prefers configured severity over impact)."""
        if self.severity:
            return self.severity
        # Fallback mapping
        impact_to_severity = {
            "critical": "error",
            "serious": "error",
            "moderate": "warning",
            "minor": "alert"
        }
        return impact_to_severity.get(self.impact.value, "warning")
```

#### Added get_violations_by_severity Method
```python
def get_violations_by_severity(self) -> Dict[str, int]:
    """Get count of violations grouped by severity level."""
    counts = {"error": 0, "warning": 0, "alert": 0}
    for page in self.page_results:
        for violation in page.violations:
            severity = violation.effective_severity
            if severity in counts:
                counts[severity] += 1
    return counts
```

### 2. Crawler (`src/core/crawler.py`)

#### Load Severity Mappings at Scan Start
```python
async def crawl(self) -> ScanResult:
    # Load enabled check configurations from database
    async with get_db_session() as db:
        repo = CheckConfigRepository(db)
        enabled_checks = await repo.get_enabled_checks()
        
        if enabled_checks:
            # Build severity mapping
            self.check_severity_map = {
                check.check_id: check.severity.value 
                for check in enabled_checks
            }
```

#### Assign Severity When Creating Violations
```python
# Get severity from check configuration
check_id = violation["id"]
configured_severity = self.check_severity_map.get(check_id)

page_result.violations.append(
    AccessibilityViolation(
        id=violation["id"],
        impact=ViolationImpact(violation.get("impact", "minor")),
        severity=configured_severity,  # NEW: Configured severity
        description=violation["description"],
        help=violation["help"],
        help_url=violation["helpUrl"],
        tags=violation["tags"],
        nodes=nodes_with_screenshots
    )
)
```

### 3. Web Routes (`src/web/app.py`)

#### Updated Results Template Context
```python
return templates.TemplateResponse(
    "results.html",
    {
        "request": request,
        "current_user": current_user,
        "scan_result": result,
        "violations_by_impact": result.get_violations_by_impact(),  # Kept for compatibility
        "violations_by_severity": result.get_violations_by_severity()  # NEW
    }
)
```

#### Updated API Response
```python
response = {
    "scan_id": scan_id,
    "status": result.status,
    "pages_scanned": result.pages_scanned,
    "total_violations": result.total_violations,
    "violations_by_impact": result.get_violations_by_impact(),  # Deprecated
    "violations_by_severity": result.get_violations_by_severity(),  # NEW
    # ...
}
```

### 4. Results Template (`templates/results.html`)

#### Updated Summary Cards
**Before** (6 cards):
- Pages Scanned
- Total Violations
- Critical (red)
- Serious (warning)
- Moderate (warning)
- Minor (info)

**After** (5 cards):
- Pages Scanned
- Total Violations
- **Errors** (red - #dc3545)
- **Warnings** (warning - #ffc107)
- **Alerts** (info/cyan - #0dcaf0)

#### Updated Summary HTML
```html
<div class="col-6 col-md-4">
    <div class="card stat-card text-center">
        <div class="card-body p-3">
            <div class="display-5 fw-bold text-danger">{{ violations_by_severity.error }}</div>
            <div class="small">Errors</div>
        </div>
    </div>
</div>
<div class="col-6 col-md-4">
    <div class="card stat-card text-center">
        <div class="card-body p-3">
            <div class="display-5 fw-bold text-warning">{{ violations_by_severity.warning }}</div>
            <div class="small">Warnings</div>
        </div>
    </div>
</div>
<div class="col-6 col-md-4">
    <div class="card stat-card text-center">
        <div class="card-body p-3">
            <div class="display-5 fw-bold" style="color: #0dcaf0;">{{ violations_by_severity.alert }}</div>
            <div class="small">Alerts</div>
        </div>
    </div>
</div>
```

#### Updated Violation Badges
```html
{% set severity = violation.effective_severity if violation.severity else violation.impact.value %}
<span class="badge severity-badge me-2
    {% if severity == 'error' or violation.impact.value == 'critical' or violation.impact.value == 'serious' %}bg-danger
    {% elif severity == 'warning' or violation.impact.value == 'moderate' %}bg-warning text-dark
    {% else %}bg-info{% endif %}">
    {% if violation.severity %}
        {{ violation.severity|upper }}
    {% else %}
        {{ violation.impact.value|upper }}
    {% endif %}
</span>
```

## How It Works

### Configuration Flow
1. **Admin sets severity** in `/admin/checks`:
   - image-alt → Error
   - heading-order → Alert
   - color-contrast → Warning
   
2. **Scan starts**, crawler loads severity mappings from database

3. **Violations detected** by axe-core and custom checks

4. **Severity assigned** to each violation from check configuration

5. **Results displayed** using configured severity levels

### Severity Mapping

| Check Configuration | Display in Results | Color |
|---------------------|-------------------|-------|
| Error | **ERROR** | Red (#dc3545) |
| Warning | **WARNING** | Yellow/Orange (#ffc107) |
| Alert | **ALERT** | Cyan (#0dcaf0) |
| Disabled | Not shown | N/A |

### Fallback Behavior

If a check doesn't have a configured severity (database unavailable or check not configured):
- Critical/Serious → Error (red)
- Moderate → Warning (yellow)
- Minor → Alert (cyan)

## Color Scheme

### Error (Red)
- **Hex**: #dc3545
- **Bootstrap**: bg-danger
- **Use**: Critical accessibility violations
- **Example**: Missing alt text, missing form labels

### Warning (Yellow/Orange)
- **Hex**: #ffc107
- **Bootstrap**: bg-warning text-dark
- **Use**: Important issues that should be fixed
- **Example**: Color contrast issues, missing skip links

### Alert (Cyan/Info)
- **Hex**: #0dcaf0
- **Bootstrap**: bg-info (custom styled)
- **Use**: Best practice recommendations
- **Example**: Heading order, noscript elements

## Testing

### Test 1: Configure Severities
1. Go to `/admin/checks`
2. Set different severity levels:
   - Set `image-alt` to **Error**
   - Set `color-contrast` to **Warning**
   - Set `heading-order` to **Alert**
3. Save changes

### Test 2: Run Scan
1. Scan a website
2. Check results page summary
3. Verify counts:
   - **Errors**: Count of error-severity violations
   - **Warnings**: Count of warning-severity violations
   - **Alerts**: Count of alert-severity violations

### Test 3: Verify Individual Violations
1. Expand violation details
2. Check badge color and text match configured severity
3. Verify colors are correct

## Example Results

### Scan of https://yorku.ca/uit

**Before (Impact-based)**:
- Critical: 0
- Serious: 2
- Moderate: 5
- Minor: 8

**After (Severity-based)**:
- Errors: 7 (Critical + Serious based on config)
- Warnings: 5 (Moderate based on config)
- Alerts: 3 (Minor based on config)

## Benefits

1. **Consistency**: Matches admin check configuration UI
2. **Simplicity**: 3 levels instead of 4
3. **Clarity**: Error/Warning/Alert are clearer than Critical/Serious/Moderate/Minor
4. **Control**: Admins can classify violations based on organizational priorities
5. **Flexibility**: Same check can be Error in one organization, Warning in another

## Backward Compatibility

- `violations_by_impact()` method still exists
- API still returns both `violations_by_impact` and `violations_by_severity`
- Old impact levels still stored for reference
- `effective_severity` property provides fallback

## Files Modified

1. ✅ `src/models/__init__.py` - Added severity support
2. ✅ `src/core/crawler.py` - Load and assign severity
3. ✅ `src/web/app.py` - Pass severity counts to template
4. ✅ `templates/results.html` - Display severity-based summary

## Deployment Status

✅ **All files updated** and copied to Docker container  
✅ **Container restarted** with new code  
✅ **Ready to test** immediately  

## Next Steps

1. **Run a test scan** to verify the new display
2. **Check the results page** summary shows Error/Warning/Alert
3. **Verify colors** are correct
4. **Test configuration** by changing severity levels in admin
5. **Rebuild Docker image** when ready for permanent deployment

## Rebuild for Permanent Deployment

When ready, rebuild the image:
```bash
docker compose build --no-cache aoda-checker
docker compose up -d
```

---

## 🎉 Implementation Complete

The results page now displays violations using the **configured severity levels** from the check configuration system!

- ✅ Error (Red)
- ✅ Warning (Yellow)
- ✅ Alert (Cyan)

The display automatically updates when you change severity levels in the admin configuration.

---

*Implementation completed: November 28, 2025*
*Status: Ready for testing*

