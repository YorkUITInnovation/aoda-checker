"""Data models for the AODA crawler."""
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class ViolationImpact(str, Enum):
    """Severity levels for accessibility violations."""
    CRITICAL = "critical"
    SERIOUS = "serious"
    MODERATE = "moderate"
    MINOR = "minor"


class AccessibilityViolation(BaseModel):
    """Model for a single accessibility violation."""
    id: str
    impact: ViolationImpact
    description: str
    help: str
    help_url: str
    tags: List[str]
    nodes: List[Dict[str, Any]] = []


class PageResult(BaseModel):
    """Model for a single page scan result."""
    url: str
    title: Optional[str] = None
    status_code: Optional[int] = None
    violations: List[AccessibilityViolation] = []
    passes: int = 0
    incomplete: int = 0
    inapplicable: int = 0
    scan_time: datetime = Field(default_factory=datetime.now)
    error: Optional[str] = None

    @property
    def violation_count(self) -> int:
        """Total number of violations."""
        return len(self.violations)

    @property
    def has_violations(self) -> bool:
        """Whether the page has any violations."""
        return self.violation_count > 0


class ScanMode(str, Enum):
    """Scan mode for accessibility testing."""
    WCAG21 = "wcag21"  # Full WCAG 2.1 Level AA
    AODA = "aoda"  # Ontario AODA/IASR requirements (WCAG 2.0 Level AA)


class ScanRequest(BaseModel):
    """Model for a scan request."""
    url: HttpUrl
    max_pages: int = Field(default=50, ge=1, le=500)
    max_depth: int = Field(default=3, ge=1, le=10)
    same_domain_only: bool = True
    restrict_to_path: bool = True
    enable_screenshots: bool = False  # Default to disabled for performance
    scan_mode: ScanMode = ScanMode.AODA  # Default to AODA requirements


class ScanResult(BaseModel):
    """Model for complete scan results."""
    scan_id: str
    start_url: str
    start_time: datetime
    end_time: Optional[datetime] = None
    pages_scanned: int = 0
    pages_with_violations: int = 0
    total_violations: int = 0
    page_results: List[PageResult] = []
    status: str = "running"  # running, completed, failed
    error_message: Optional[str] = None

    # Scan configuration
    max_pages: int = 50
    max_depth: int = 3
    same_domain_only: bool = True
    restrict_to_path: bool = True
    scan_mode: str = "aoda"  # Store as string for database compatibility

    @property
    def duration(self) -> Optional[float]:
        """Scan duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def get_violations_by_impact(self) -> Dict[str, int]:
        """Get count of violations grouped by impact level."""
        counts = {impact.value: 0 for impact in ViolationImpact}
        for page in self.page_results:
            for violation in page.violations:
                counts[violation.impact.value] += 1
        return counts

