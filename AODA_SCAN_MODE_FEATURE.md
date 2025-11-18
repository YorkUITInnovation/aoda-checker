# AODA Scan Mode Feature Implementation

## Overview
This document describes the implementation of dual scan modes for the AODA Compliance Checker:
1. **Ontario AODA/IASR** (default) - WCAG 2.0 Level AA
2. **WCAG 2.1** - Full WCAG 2.1 Level AA

## Changes Made

### 1. Core Models (`src/models/__init__.py`)
- Added `ScanMode` enum with two values: `AODA` and `WCAG21`
- Added `scan_mode` field to `ScanRequest` model (default: `ScanMode.AODA`)
- Added `scan_mode` field to `ScanResult` model (stored as string for database compatibility)

### 2. AODA Requirements Module (`src/utils/aoda_requirements.py`)
Created a new module that defines:
- **AODA requirements**: Based on WCAG 2.0 Level A and AA (required by Ontario's IASR)
- **WCAG 2.1 requirements**: Full WCAG 2.1 Level AA compliance
- **Configuration functions**:
  - `get_aoda_axe_config()`: Returns axe-core config for AODA scanning
  - `get_wcag21_axe_config()`: Returns axe-core config for WCAG 2.1 scanning
  - `get_axe_config_for_scan_mode(scan_mode)`: Returns appropriate config based on mode

#### AODA Configuration
The AODA scan mode targets WCAG 2.0 Level A and AA tags:
```python
{
    "runOnly": {
        "type": "tag",
        "values": ["wcag2a", "wcag2aa", "wcag20"]
    }
}
```

#### WCAG 2.1 Configuration
The WCAG 2.1 scan mode includes additional 2.1 criteria:
```python
{
    "runOnly": {
        "type": "tag",
        "values": ["wcag2a", "wcag2aa", "wcag21"]
    }
}
```

### 3. Crawler Updates (`src/core/crawler.py`)
- Modified `__init__` to accept and store `scan_mode` from `ScanRequest`
- Updated `crawl()` method to log which scan mode is being used
- Modified `_scan_page()` to pass scan mode configuration to axe-core:
  ```python
  from src.utils.aoda_requirements import get_axe_config_for_scan_mode
  axe = Axe()
  axe_config = get_axe_config_for_scan_mode(self.scan_mode)
  axe_results = await axe.run(page, options=axe_config)
  ```

### 4. Database Updates

#### Models (`src/database/models.py`)
- Added `scan_mode` column to `Scan` table:
  ```python
  scan_mode = Column(String(20), nullable=False, default="aoda")
  ```
- Updated `to_scan_result()` method to include scan_mode

#### Repository (`src/database/repository.py`)
- Updated `create_scan()` to store scan_mode value

#### Migration Script (`scripts/add_scan_mode_column.py`)
Created migration script to add the `scan_mode` column to existing databases:
- Checks if column already exists
- Adds column with default value 'aoda'
- Safe to run multiple times (idempotent)

### 5. User Interface Updates

#### Scan Form (`templates/index.html`)
Added scan mode selection dropdown:
```html
<select class="form-select" id="scanMode" name="scanMode">
    <option value="aoda" selected>Ontario AODA/IASR (WCAG 2.0 Level AA)</option>
    <option value="wcag21">Full WCAG 2.1 Level AA</option>
</select>
```

Includes helpful description:
- **AODA**: Complies with Ontario's accessibility requirements (WCAG 2.0 AA)
- **WCAG 2.1**: Includes additional criteria beyond AODA requirements

JavaScript form submission updated to include `scan_mode` field.

#### Results Page (`templates/results.html`)
Added display of scan mode used:
```html
<i class="bi bi-shield-check"></i> 
{% if scan_result.scan_mode == 'aoda' %}
    <strong>Ontario AODA/IASR</strong> (WCAG 2.0 Level AA)
{% else %}
    <strong>WCAG 2.1 Level AA</strong>
{% endif %}
```

#### History Page (`templates/history.html`)
Updated scan cards to show scan mode:
```javascript
<i class="bi bi-shield-check"></i>
${scan.scan_mode === 'aoda' ? 'Ontario AODA' : 'WCAG 2.1'}
```

## Usage

### For Users
1. **Start a new scan** from the homepage
2. **Select scan mode** from the dropdown:
   - **Ontario AODA/IASR** (default): For compliance with Ontario regulations
   - **Full WCAG 2.1 Level AA**: For broader accessibility coverage
3. **Submit the scan** - results will indicate which mode was used

### For Developers
The scan mode is automatically passed through the entire scanning pipeline:
1. User selects mode in UI
2. `ScanRequest` created with selected `scan_mode`
3. Crawler receives mode and configures axe-core accordingly
4. Results are stored with scan_mode for reference
5. History and results pages display which mode was used

## Database Migration

To add the scan_mode column to an existing database:

```bash
python scripts/add_scan_mode_column.py
```

Or from Docker:
```bash
docker exec -it aoda-compliance-checker python scripts/add_scan_mode_column.py
```

## Technical Details

### Why Two Modes?

1. **AODA/IASR Mode** (WCAG 2.0 Level AA):
   - Required by Ontario's Integrated Accessibility Standards Regulation
   - Focuses on WCAG 2.0 Level A and AA criteria
   - May produce fewer violations than WCAG 2.1 for the same page
   - Suitable for organizations that must comply with AODA

2. **WCAG 2.1 Mode** (Full Level AA):
   - Includes all WCAG 2.1 Level AA criteria
   - Additional success criteria beyond WCAG 2.0
   - More comprehensive accessibility coverage
   - Suitable for organizations aiming for broader accessibility

### Axe-Core Tag System

Axe-core uses tags to categorize rules. The scanner uses these tags:
- `wcag2a`: WCAG 2.0 Level A criteria
- `wcag2aa`: WCAG 2.0 Level AA criteria  
- `wcag20`: All WCAG 2.0 criteria
- `wcag21`: All WCAG 2.1 criteria (additional to 2.0)

## Default Behavior

- **Default scan mode**: AODA (Ontario AODA/IASR)
- **Backward compatibility**: Existing scans without scan_mode will default to 'aoda'
- **Database default**: New scan records default to 'aoda' if not specified

## Benefits

1. **Compliance Focused**: Default mode ensures AODA compliance
2. **Flexibility**: Option to scan with stricter WCAG 2.1 criteria
3. **Transparency**: Results clearly show which standard was used
4. **Informed Decisions**: Organizations can choose appropriate scanning level
5. **Historical Tracking**: Can compare results between scan modes over time

