# ARIA Requirements and Ontario AODA Compliance

## Question
Are ARIA (Accessible Rich Internet Applications) errors part of Ontario AODA requirements?

## Answer: YES ✅

**ARIA errors ARE part of Ontario AODA requirements and MUST be included in AODA scans.**

## Why ARIA is Required by AODA

### 1. Legal Requirement Chain

```
Ontario AODA/IASR
    ↓
Requires WCAG 2.0 Level AA
    ↓
Includes WCAG 2.0 Level A
    ↓
Includes Success Criterion 4.1.2 "Name, Role, Value"
    ↓
Requires proper ARIA implementation
```

### 2. WCAG 2.0 Success Criterion 4.1.2

**Success Criterion 4.1.2 Name, Role, Value (Level A)**

> For all user interface components, the name and role can be programmatically determined; states, properties, and values that can be set by the user can be programmatically set; and notification of changes to these items is available to user agents, including assistive technologies.

This criterion specifically requires:
- **Name**: Components must have accessible names
- **Role**: Components must have proper roles (ARIA roles)
- **Value**: States and properties must be programmatically determinable
- **Notification**: Changes must be communicated to assistive technologies

**ARIA is the primary mechanism for meeting this criterion in modern web applications.**

### 3. Ontario AODA Timeline

- **January 1, 2014**: WCAG 2.0 Level A required
- **January 1, 2021**: WCAG 2.0 Level AA required

Since SC 4.1.2 is Level A, ARIA compliance has been required since 2014.

## ARIA Rules Included in AODA Scanning

All of the following ARIA rules are part of AODA compliance because they enforce WCAG 2.0 SC 4.1.2:

### Core ARIA Rules
- ✅ `aria-allowed-attr` - Only allow supported ARIA attributes on elements
- ✅ `aria-required-attr` - ARIA roles must have required attributes
- ✅ `aria-required-children` - Elements with ARIA roles requiring child elements
- ✅ `aria-required-parent` - Elements with ARIA roles requiring parent elements
- ✅ `aria-roles` - ARIA role values must be valid
- ✅ `aria-valid-attr` - ARIA attributes must be valid
- ✅ `aria-valid-attr-value` - ARIA attribute values must be valid

### ARIA Naming Rules
- ✅ `aria-command-name` - Command elements must have accessible names
- ✅ `aria-dialog-name` - Dialog elements must have accessible names
- ✅ `aria-input-field-name` - Input fields must have accessible names
- ✅ `aria-meter-name` - Meter elements must have accessible names
- ✅ `aria-progressbar-name` - Progress bars must have accessible names
- ✅ `aria-toggle-field-name` - Toggle fields must have accessible names
- ✅ `aria-tooltip-name` - Tooltips must have accessible names

### ARIA Visibility Rules
- ✅ `aria-hidden-body` - aria-hidden must not be on the document body
- ✅ `aria-hidden-focus` - aria-hidden elements must not contain focusable elements

## WCAG 2.0 vs WCAG 2.1 - Important Distinction

### What AODA Requires
- **WCAG 2.0 Level AA** (as of January 1, 2021)

### ARIA in WCAG 2.0 vs 2.1
- **WCAG 2.0**: Introduced ARIA requirements via SC 4.1.2
- **WCAG 2.1**: Did NOT change ARIA requirements (they remain the same)
- **WCAG 2.1**: Added NEW criteria (Orientation, Reflow, Text Spacing, etc.) but ARIA rules stayed the same

**Therefore**: ARIA requirements are the SAME in both WCAG 2.0 and WCAG 2.1

## Why This Matters for Your Scanner

### Current Implementation: ✅ CORRECT

Your AODA scanner currently includes ARIA rules, which is **correct and legally required**.

The scanner uses:
```python
{
    "runOnly": {
        "type": "tag",
        "values": ["wcag2a", "wcag2aa", "wcag20"]
    }
}
```

This configuration:
- ✅ Includes all WCAG 2.0 Level A rules (including ARIA via SC 4.1.2)
- ✅ Includes all WCAG 2.0 Level AA rules
- ✅ Excludes WCAG 2.1-specific rules (like Orientation, Reflow, etc.)
- ✅ **Includes ALL ARIA rules** (because they're from WCAG 2.0)

## What Would Happen If You Removed ARIA Rules?

### ❌ Legal Compliance Issues
1. **Not AODA compliant** - Missing WCAG 2.0 SC 4.1.2
2. **Not WCAG 2.0 Level A compliant** - SC 4.1.2 is Level A
3. **Government/public sector websites would fail legal requirements**

### ❌ Accessibility Issues
1. Screen readers couldn't properly identify interactive elements
2. Keyboard navigation would be broken
3. Dynamic content changes wouldn't be announced
4. Form controls would be unlabeled
5. Custom widgets would be inaccessible

### ❌ Real-World Impact
- Users with disabilities couldn't use the website
- Organizations could face accessibility complaints
- Legal action possible under AODA

## Examples of ARIA in Practice

### Example 1: Custom Button
```html
<!-- ❌ FAILS AODA - Missing role and name -->
<div onclick="submit()"></div>

<!-- ✅ PASSES AODA - Has proper ARIA -->
<div role="button" aria-label="Submit form" onclick="submit()"></div>
```

### Example 2: Modal Dialog
```html
<!-- ❌ FAILS AODA - Missing ARIA attributes -->
<div class="modal">
  <h2>Confirm Action</h2>
  <button>OK</button>
</div>

<!-- ✅ PASSES AODA - Proper ARIA implementation -->
<div role="dialog" aria-labelledby="dialog-title" aria-modal="true">
  <h2 id="dialog-title">Confirm Action</h2>
  <button>OK</button>
</div>
```

### Example 3: Live Region
```html
<!-- ❌ FAILS AODA - Status updates not announced -->
<div id="status">Processing...</div>

<!-- ✅ PASSES AODA - Updates announced to screen readers -->
<div id="status" role="status" aria-live="polite">Processing...</div>
```

## Official References

### Ontario Government
- [AODA - Ontario.ca](https://www.ontario.ca/laws/statute/05a11)
- [IASR Web Accessibility Requirements](https://www.ontario.ca/page/how-make-websites-accessible)

### WCAG Documentation
- [WCAG 2.0 SC 4.1.2 Name, Role, Value](https://www.w3.org/WAI/WCAG21/Understanding/name-role-value.html)
- [Using ARIA](https://www.w3.org/WAI/ARIA/apg/)

### Axe-core Rules
- [Axe-core Rule Descriptions](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)

## Conclusion

### Final Answer: ARIA MUST Stay in AODA Scans ✅

**Do NOT remove ARIA rules from AODA scanning.** They are:
1. ✅ Legally required by Ontario AODA
2. ✅ Part of WCAG 2.0 Level A (SC 4.1.2)
3. ✅ Essential for accessibility
4. ✅ The same in WCAG 2.0 and 2.1

### Current Implementation: Perfect ✅

Your scanner is correctly configured:
- AODA mode: Scans for WCAG 2.0 AA (includes ARIA)
- WCAG 2.1 mode: Scans for WCAG 2.1 AA (includes same ARIA + additional criteria)

**No changes needed - the implementation is correct!**

## Summary Table

| Aspect | AODA Requirement | Scanner Implementation | Status |
|--------|------------------|------------------------|--------|
| WCAG Version | WCAG 2.0 Level AA | Uses wcag20, wcag2a, wcag2aa tags | ✅ Correct |
| ARIA Rules | Required (SC 4.1.2) | Included via wcag2a tag | ✅ Correct |
| WCAG 2.1 Rules | Not required | Excluded (only in WCAG 2.1 mode) | ✅ Correct |
| Legal Compliance | AODA/IASR compliant | Yes | ✅ Correct |

---

**The scanner is working correctly. ARIA errors are properly included in AODA scans as required by law.**

