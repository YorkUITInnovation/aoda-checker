"""Custom accessibility checks to supplement axe-core."""
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup, Tag


class CustomChecker:
    """Custom accessibility checks not covered by axe-core."""
    
    def __init__(self, html_content: str, url: str):
        """Initialize checker with HTML content."""
        self.html = html_content
        self.url = url
        self.soup = BeautifulSoup(html_content, 'html.parser')
        
    def run_all_checks(self) -> List[Dict[str, Any]]:
        """Run all custom checks and return violations."""
        violations = []
        
        # Run each check
        violations.extend(self.check_spacer_images())
        violations.extend(self.check_noscript_elements())
        
        return violations
    
    def check_spacer_images(self) -> List[Dict[str, Any]]:
        """Check for decorative/spacer images that incorrectly have alt text instead of alt=\"\"."""
        violations = []
        
        # Find all images
        images = self.soup.find_all('img')
        
        for img in images:
            src = img.get('src', '').lower()
            alt = img.get('alt')
            width = img.get('width', '')
            height = img.get('height', '')
            
            # Check if image looks like a spacer/decorative image
            is_spacer = False
            reasons = []
            
            # Check for common spacer image names
            spacer_patterns = [
                r'spacer',
                r'blank',
                r'transparent',
                r'pixel',
                r'1x1',
                r'dot\.gif',
                r'clear\.gif',
                r'shim',
            ]
            
            for pattern in spacer_patterns:
                if re.search(pattern, src):
                    is_spacer = True
                    reasons.append(f"filename contains '{pattern}'")
                    break
            
            # Check for 1px dimensions
            try:
                if (width == '1' or height == '1') or (width == 1 or height == 1):
                    is_spacer = True
                    reasons.append("1px dimension")
            except (ValueError, TypeError):
                pass
            
            # If it's a spacer image and alt is NOT empty string, flag it
            # (Decorative images should have alt="" to be hidden from screen readers)
            if is_spacer and alt != '':
                # Get the element selector
                selector = self._get_selector(img)
                
                violations.append({
                    "id": "spacer-image-alt",
                    "impact": "moderate",
                    "description": "Decorative spacer images should have empty alt attribute (alt=\"\")",
                    "help": "Decorative/spacer images should have alt=\"\" to hide them from screen readers, not descriptive text",
                    "helpUrl": "https://www.w3.org/WAI/WCAG21/Understanding/non-text-content.html",
                    "tags": ["cat.text-alternatives", "wcag2a", "wcag111", "custom"],
                    "nodes": [{
                        "target": [selector],
                        "html": str(img)[:200],
                        "failureSummary": f"Decorative spacer image has alt=\"{alt}\" but should have alt=\"\" ({', '.join(reasons)})"
                    }]
                })
        
        return violations
    
    def check_noscript_elements(self) -> List[Dict[str, Any]]:
        """Check for noscript elements (indicates potential JavaScript dependency)."""
        violations = []
        
        noscripts = self.soup.find_all('noscript')
        
        if noscripts:
            for noscript in noscripts:
                selector = self._get_selector(noscript)
                
                violations.append({
                    "id": "noscript-element",
                    "impact": "minor",
                    "description": "Noscript elements detected - ensure functionality is available without JavaScript",
                    "help": "Pages should be functional without JavaScript, or provide equivalent alternatives",
                    "helpUrl": "https://www.w3.org/TR/WCAG20-TECHS/G173.html",
                    "tags": ["cat.parsing", "best-practice", "custom"],
                    "nodes": [{
                        "target": [selector],
                        "html": str(noscript)[:200],
                        "failureSummary": "Noscript element found - verify JavaScript alternatives are accessible"
                    }]
                })
        
        return violations
    
    def _get_selector(self, element: Tag) -> str:
        """Generate a CSS selector for an element."""
        # Try to use ID if available
        if element.get('id'):
            return f"#{element['id']}"
        
        # Try to use unique class
        if element.get('class'):
            classes = ' '.join(element['class'])
            return f"{element.name}.{element['class'][0]}"
        
        # Fall back to tag name with index
        parent = element.parent
        if parent:
            siblings = [s for s in parent.find_all(element.name, recursive=False)]
            if len(siblings) > 1:
                index = siblings.index(element) + 1
                return f"{element.name}:nth-of-type({index})"
        
        return element.name


class ViolationAggregator:
    """Combines violations from axe-core and custom checks, applying configuration."""
    
    def __init__(self, check_configs: Dict[str, Dict[str, Any]]):
        """
        Initialize with check configurations.
        
        Args:
            check_configs: Dictionary mapping check_id to configuration
                          (enabled, severity, etc.)
        """
        self.check_configs = check_configs
    
    def aggregate_violations(
        self,
        axe_violations: List[Dict[str, Any]],
        custom_violations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Combine and filter violations based on configuration.
        
        Args:
            axe_violations: Violations from axe-core
            custom_violations: Violations from custom checks
            
        Returns:
            Filtered and configured list of violations
        """
        all_violations = []
        
        # Process axe violations
        for violation in axe_violations:
            check_id = violation.get('id')
            config = self.check_configs.get(check_id, {})
            
            # Skip if disabled
            if not config.get('enabled', True):
                continue
            
            # Apply configured severity if available
            if 'severity' in config:
                severity = config['severity']
                # Map severity to impact
                severity_to_impact = {
                    'error': 'serious',
                    'warning': 'moderate',
                    'alert': 'minor'
                }
                violation['impact'] = severity_to_impact.get(severity, violation.get('impact', 'moderate'))
            
            all_violations.append(violation)
        
        # Process custom violations
        for violation in custom_violations:
            check_id = violation.get('id')
            config = self.check_configs.get(check_id, {})
            
            # Skip if disabled
            if not config.get('enabled', True):
                continue
            
            # Apply configured severity if available
            if 'severity' in config:
                severity = config['severity']
                severity_to_impact = {
                    'error': 'serious',
                    'warning': 'moderate',
                    'alert': 'minor'
                }
                violation['impact'] = severity_to_impact.get(severity, violation.get('impact', 'moderate'))
            
            all_violations.append(violation)
        
        return all_violations

