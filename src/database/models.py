"""Database models and ORM configuration."""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON, ForeignKey, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import enum

Base = declarative_base()


class ScanStatus(str, enum.Enum):
    """Scan status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    id_number = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Authentication method (for future extensibility)
    auth_method = Column(String(50), default="manual", nullable=False)  # manual, saml, oauth, ldap, etc.

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    scans = relationship("Scan", back_populates="user", cascade="all, delete-orphan")

    @property
    def full_name(self):
        """Computed property for backward compatibility."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or ""

    def __repr__(self):
        return f"<User(username={self.username}, is_admin={self.is_admin})>"


class Scan(Base):
    """Scan record in database."""
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(String(36), unique=True, index=True, nullable=False)
    start_url = Column(String(2048), nullable=False)
    status = Column(Enum(ScanStatus), default=ScanStatus.PENDING, nullable=False)

    # User association
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Configuration
    max_pages = Column(Integer, nullable=False)
    max_depth = Column(Integer, nullable=False)
    same_domain_only = Column(Integer, nullable=False)  # MySQL doesn't have native boolean
    scan_mode = Column(String(20), nullable=False, default="aoda")  # 'aoda' or 'wcag21'

    # Results
    pages_scanned = Column(Integer, default=0)
    pages_with_violations = Column(Integer, default=0)
    total_violations = Column(Integer, default=0)

    # Timestamps
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="scans")
    pages = relationship("PageScan", back_populates="scan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Scan(scan_id={self.scan_id}, url={self.start_url}, status={self.status})>"

    def to_scan_result(self):
        """Convert database model to ScanResult Pydantic model."""
        from src.models import ScanResult, PageResult, AccessibilityViolation, ViolationImpact

        # Convert page scans
        page_results = []
        for page in self.pages:
            violations = []
            for viol in page.violations:
                violations.append(
                    AccessibilityViolation(
                        id=viol.violation_id,
                        impact=ViolationImpact(viol.impact),
                        description=viol.description,
                        help=viol.help,
                        help_url=viol.help_url,
                        tags=viol.tags,
                        nodes=viol.nodes
                    )
                )

            page_results.append(
                PageResult(
                    url=page.url,
                    title=page.title,
                    status_code=page.status_code,
                    violations=violations,
                    passes=page.passes,
                    incomplete=page.incomplete,
                    inapplicable=page.inapplicable,
                    scan_time=page.scanned_at,
                    error=page.error
                )
            )

        # Determine status string
        status_map = {
            ScanStatus.PENDING: "pending",
            ScanStatus.IN_PROGRESS: "running",
            ScanStatus.COMPLETED: "completed",
            ScanStatus.FAILED: "failed"
        }

        return ScanResult(
            scan_id=self.scan_id,
            start_url=self.start_url,
            start_time=self.start_time,
            end_time=self.end_time,
            pages_scanned=self.pages_scanned,
            pages_with_violations=self.pages_with_violations,
            total_violations=self.total_violations,
            page_results=page_results,
            status=status_map.get(self.status, "unknown"),
            error_message=self.error_message,
            max_pages=self.max_pages,
            max_depth=self.max_depth,
            same_domain_only=bool(self.same_domain_only),
            restrict_to_path=True,  # Default, not stored in DB yet
            scan_mode=self.scan_mode if hasattr(self, 'scan_mode') else 'aoda'
        )


class PageScan(Base):
    """Individual page scan result."""
    __tablename__ = "page_scans"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False, index=True)

    url = Column(String(2048), nullable=False)
    title = Column(String(512), nullable=True)
    status_code = Column(Integer, nullable=True)

    # Statistics
    violation_count = Column(Integer, default=0)
    passes = Column(Integer, default=0)
    incomplete = Column(Integer, default=0)
    inapplicable = Column(Integer, default=0)

    # Error handling
    error = Column(Text, nullable=True)

    # Timestamps
    scanned_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    scan = relationship("Scan", back_populates="pages")
    violations = relationship("Violation", back_populates="page", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PageScan(url={self.url}, violations={self.violation_count})>"


class Violation(Base):
    """Accessibility violation found on a page."""
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("page_scans.id"), nullable=False, index=True)

    violation_id = Column(String(128), nullable=False)  # axe rule id
    impact = Column(String(32), nullable=False)  # critical, serious, moderate, minor
    description = Column(Text, nullable=False)
    help = Column(String(512), nullable=False)
    help_url = Column(String(512), nullable=False)

    # Store tags and nodes as JSON
    tags = Column(JSON, nullable=False)
    nodes = Column(JSON, nullable=False)  # Array of affected elements

    # Timestamps
    found_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    page = relationship("PageScan", back_populates="violations")

    def __repr__(self):
        return f"<Violation(id={self.violation_id}, impact={self.impact})>"


class CheckSeverity(str, enum.Enum):
    """Severity level for accessibility checks."""
    ERROR = "error"
    WARNING = "warning"
    ALERT = "alert"
    DISABLED = "disabled"


class CheckConfiguration(Base):
    """Configuration for individual accessibility checks."""
    __tablename__ = "check_configurations"

    id = Column(Integer, primary_key=True, index=True)

    # Check identification
    check_id = Column(String(128), unique=True, index=True, nullable=False)  # e.g., 'image-alt', 'empty-heading'
    check_name = Column(String(255), nullable=False)  # Human-readable name
    description = Column(Text, nullable=True)  # Description of what the check does

    # Configuration
    enabled = Column(Boolean, default=True, nullable=False)  # Whether check is enabled
    severity = Column(Enum(CheckSeverity), default=CheckSeverity.ERROR, nullable=False)  # error, warning, or alert

    # WCAG/AODA mapping
    wcag_criterion = Column(String(128), nullable=True)  # e.g., '1.1.1', '2.4.6'
    wcag_level = Column(String(10), nullable=True)  # 'A', 'AA', 'AAA'
    aoda_required = Column(Boolean, default=False, nullable=False)  # Required by AODA
    wcag21_only = Column(Boolean, default=False, nullable=False)  # Only in WCAG 2.1, not 2.0

    # Check type
    check_type = Column(String(50), default='axe', nullable=False)  # 'axe', 'custom', 'html-cs'

    # Metadata
    help_url = Column(String(512), nullable=True)
    tags = Column(JSON, nullable=True)  # Array of relevant tags

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CheckConfiguration(check_id={self.check_id}, enabled={self.enabled}, severity={self.severity})>"


class UserCheckConfiguration(Base):
    """User-specific overrides for check configurations."""
    __tablename__ = "user_check_configurations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    check_id = Column(String(128), ForeignKey("check_configurations.check_id", ondelete="CASCADE"), nullable=False, index=True)

    # User-specific settings (override defaults)
    enabled = Column(Boolean, default=True, nullable=False)
    severity = Column(Enum(CheckSeverity), default=CheckSeverity.ERROR, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="check_configurations")
    check = relationship("CheckConfiguration")

    def __repr__(self):
        return f"<UserCheckConfiguration(user_id={self.user_id}, check_id={self.check_id}, enabled={self.enabled})>"

