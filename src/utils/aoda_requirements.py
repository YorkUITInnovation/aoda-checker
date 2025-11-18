"""
AODA (Accessibility for Ontarians with Disabilities Act) Requirements Parser.

This module maps AODA requirements to WCAG 2.0/2.1 success criteria.
Ontario's IASR (Integrated Accessibility Standards Regulation) requires
compliance with WCAG 2.0 Level AA.

IMPORTANT: ARIA Requirements and AODA
======================================
ARIA (Accessible Rich Internet Applications) errors ARE part of Ontario AODA requirements.

Why ARIA is included in AODA:
1. Ontario AODA/IASR requires WCAG 2.0 Level A and AA compliance
2. WCAG 2.0 Success Criterion 4.1.2 "Name, Role, Value" (Level A) requires:
   - User interface components have accessible names and roles
   - States, properties, and values can be programmatically determined
   - User agents (including assistive technologies) are notified of changes
3. ARIA attributes are the primary mechanism for meeting SC 4.1.2 in web applications
4. Therefore, proper ARIA usage is mandatory for AODA compliance

ARIA Rules Included in AODA Scanning:
- aria-allowed-attr: Only allow supported ARIA attributes
- aria-required-attr: ARIA roles must have required attributes
- aria-required-children: ARIA roles with required children
- aria-required-parent: ARIA roles with required parent
- aria-roles: ARIA roles must be valid
- aria-valid-attr: ARIA attributes must be valid
- aria-valid-attr-value: ARIA attribute values must be valid
- aria-*-name: Various ARIA elements must have accessible names
- aria-hidden-*: Proper use of aria-hidden

All these rules map to WCAG 2.0 SC 4.1.2 (Level A) which is required by AODA.

WCAG 2.0 vs 2.1 Difference:
- AODA requires: WCAG 2.0 Level AA
- WCAG 2.1 added: Additional success criteria (e.g., Orientation, Reflow, etc.)
- WCAG 2.1 did NOT change ARIA requirements - they remain from WCAG 2.0
"""

# AODA Web Accessibility Requirements based on IASR O. Reg. 191/11
# These map to WCAG 2.0 Level A and AA criteria only
# Ontario AODA/IASR requires WCAG 2.0 Level AA compliance

AODA_WCAG_TAGS = [
    # WCAG 2.0 Level A and AA tags only
    "wcag2a",
    "wcag2aa",
    "wcag20",
    # Note: wcag21 is NOT included as AODA only requires WCAG 2.0
]

# Exclude WCAG 2.1 AAA and other non-required tags
EXCLUDED_TAGS = [
    "wcag2aaa",
    "wcag22",
    "wcag22aa",
    "best-practice",
    "experimental",
]

# Core AODA/IASR requirements aligned with WCAG 2.0 Level AA
# These are the axe-core rule IDs that align with AODA requirements
AODA_REQUIRED_RULES = [
    # Perceivable
    "area-alt",  # 1.1.1 Non-text Content
    "image-alt",  # 1.1.1 Non-text Content
    "input-image-alt",  # 1.1.1 Non-text Content
    "object-alt",  # 1.1.1 Non-text Content
    "audio-caption",  # 1.2.1 Audio-only and Video-only (Prerecorded)
    "video-caption",  # 1.2.2 Captions (Prerecorded)
    "color-contrast",  # 1.4.3 Contrast (Minimum)
    "color-contrast-enhanced",  # 1.4.6 Contrast (Enhanced) - for AAA but often included
    
    # Operable
    "accesskeys",  # 2.1.1 Keyboard
    "button-name",  # 2.1.1 Keyboard / 4.1.2 Name, Role, Value
    "bypass",  # 2.4.1 Bypass Blocks
    "duplicate-id",  # 4.1.1 Parsing
    "focus-order-semantics",  # 2.4.3 Focus Order
    "frame-title",  # 2.4.1 Bypass Blocks / 4.1.2 Name, Role, Value
    "link-name",  # 2.4.4 Link Purpose (In Context)
    "page-has-heading-one",  # 2.4.6 Headings and Labels
    "tabindex",  # 2.1.1 Keyboard
    
    # Understandable
    "document-title",  # 2.4.2 Page Titled
    "html-has-lang",  # 3.1.1 Language of Page
    "html-lang-valid",  # 3.1.1 Language of Page
    "label",  # 3.3.2 Labels or Instructions
    "valid-lang",  # 3.1.2 Language of Parts
    
    # Robust
    "aria-allowed-attr",  # 4.1.2 Name, Role, Value
    "aria-command-name",  # 4.1.2 Name, Role, Value
    "aria-dialog-name",  # 4.1.2 Name, Role, Value
    "aria-hidden-body",  # 4.1.2 Name, Role, Value
    "aria-hidden-focus",  # 4.1.2 Name, Role, Value
    "aria-input-field-name",  # 4.1.2 Name, Role, Value
    "aria-meter-name",  # 4.1.2 Name, Role, Value
    "aria-progressbar-name",  # 4.1.2 Name, Role, Value
    "aria-required-attr",  # 4.1.2 Name, Role, Value
    "aria-required-children",  # 4.1.2 Name, Role, Value
    "aria-required-parent",  # 4.1.2 Name, Role, Value
    "aria-roles",  # 4.1.2 Name, Role, Value
    "aria-toggle-field-name",  # 4.1.2 Name, Role, Value
    "aria-tooltip-name",  # 4.1.2 Name, Role, Value
    "aria-valid-attr-value",  # 4.1.2 Name, Role, Value
    "aria-valid-attr",  # 4.1.2 Name, Role, Value
    "definition-list",  # 1.3.1 Info and Relationships
    "dlitem",  # 1.3.1 Info and Relationships
    "empty-heading",  # 2.4.6 Headings and Labels
    "form-field-multiple-labels",  # 3.3.2 Labels or Instructions
    "heading-order",  # 1.3.1 Info and Relationships
    "list",  # 1.3.1 Info and Relationships
    "listitem",  # 1.3.1 Info and Relationships
    "meta-refresh",  # 2.2.1 Timing Adjustable
    "meta-viewport",  # 1.4.4 Resize text
    "region",  # 1.3.1 Info and Relationships
    "scope-attr-valid",  # 1.3.1 Info and Relationships
    "table-duplicate-name",  # 1.3.1 Info and Relationships
    "td-headers-attr",  # 1.3.1 Info and Relationships
    "th-has-data-cells",  # 1.3.1 Info and Relationships
]


def get_aoda_axe_config():
    """
    Get axe-core configuration for AODA compliance scanning.
    
    This configuration focuses on WCAG 2.0 Level A and AA criteria,
    which are required by Ontario's IASR.
    
    Important: This configuration INCLUDES ARIA requirements because:
    - ARIA is part of WCAG 2.0 Success Criterion 4.1.2 (Level A)
    - WCAG 2.0 Level A is required by Ontario AODA
    - Therefore ARIA compliance is mandatory for AODA

    Tags used:
    - wcag2a: WCAG 2.0 Level A (includes ARIA/SC 4.1.2)
    - wcag2aa: WCAG 2.0 Level AA
    - wcag20: All WCAG 2.0 rules (ensures no WCAG 2.1-only rules)

    Returns:
        dict: Configuration object for axe-core
    """
    return {
        "runOnly": {
            "type": "tag",
            "values": ["wcag2a", "wcag2aa", "wcag20"]
        }
    }


def get_wcag21_axe_config():
    """
    Get axe-core configuration for full WCAG 2.1 Level AA compliance scanning.
    
    Returns:
        dict: Configuration object for axe-core
    """
    return {
        "runOnly": {
            "type": "tag",
            "values": ["wcag2a", "wcag2aa", "wcag21"]
        }
    }


def get_axe_config_for_scan_mode(scan_mode: str):
    """
    Get the appropriate axe-core configuration based on scan mode.
    
    Args:
        scan_mode: Either 'aoda' or 'wcag21'
        
    Returns:
        dict: Configuration object for axe-core
    """
    if scan_mode == "aoda":
        return get_aoda_axe_config()
    else:
        return get_wcag21_axe_config()

