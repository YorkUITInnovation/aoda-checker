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


class ScheduleFrequency(str, enum.Enum):
    """Frequency for scheduled scans."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class ScheduledScan(Base):
    """Scheduled scan configuration."""
    __tablename__ = "scheduled_scans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Scan configuration
    start_url = Column(String(2048), nullable=False)
    max_pages = Column(Integer, nullable=False, default=50)
    max_depth = Column(Integer, nullable=False, default=3)
    same_domain_only = Column(Integer, nullable=False, default=1)
    # Note: Scheduled scans use user's check configuration from user_check_configurations table

    # Schedule configuration
    frequency = Column(Enum(ScheduleFrequency), nullable=False)
    schedule_time = Column(String(5), nullable=False)  # HH:MM format (24-hour)
    day_of_week = Column(Integer, nullable=True)  # 0=Monday, 6=Sunday (for weekly)
    day_of_month = Column(Integer, nullable=True)  # 1-31 (for monthly)
    month_of_year = Column(Integer, nullable=True)  # 1-12 (for yearly)

    # Email notification settings
    email_notifications = Column(Boolean, default=True, nullable=False)
    notify_on_violations = Column(Boolean, default=True, nullable=False)
    notify_on_errors = Column(Boolean, default=True, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="scheduled_scans")
    logs = relationship("ScheduledScanLog", back_populates="scheduled_scan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ScheduledScan(id={self.id}, url={self.start_url}, frequency={self.frequency}, active={self.is_active})>"


class ScheduledScanLogStatus(str, enum.Enum):
    """Status of scheduled scan execution."""
    SUCCESS = "success"
    FAILED = "failed"


class ScheduledScanLog(Base):
    """Log entry for scheduled scan execution."""
    __tablename__ = "scheduled_scan_logs"

    id = Column(Integer, primary_key=True, index=True)
    scheduled_scan_id = Column(Integer, ForeignKey("scheduled_scans.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Execution details
    start_url = Column(String(2048), nullable=False)
    status = Column(Enum(ScheduledScanLogStatus), nullable=False)

    # Scan result
    scan_id = Column(String(36), nullable=True)  # Reference to the actual scan created (if successful)
    pages_scanned = Column(Integer, default=0)
    total_violations = Column(Integer, default=0)

    # Error information (if failed)
    error_message = Column(Text, nullable=True)

    # Execution time
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    duration_seconds = Column(Integer, nullable=True)  # How long the scan took

    # Email notification status
    email_sent = Column(Boolean, default=False, nullable=False)

    # Relationships
    scheduled_scan = relationship("ScheduledScan", back_populates="logs")
    user = relationship("User", backref="scheduled_scan_logs")

    def __repr__(self):
        return f"<ScheduledScanLog(id={self.id}, url={self.start_url}, status={self.status}, executed_at={self.executed_at})>"


class SAMLConfiguration(Base):
    """SAML2 authentication configuration."""
    __tablename__ = "saml_configurations"

    id = Column(Integer, primary_key=True, index=True)

    # SAML enabled status
    enabled = Column(Boolean, default=False, nullable=False)

    # Service Provider (SP) Configuration
    sp_entity_id = Column(String(512), nullable=True)
    sp_acs_url = Column(String(512), nullable=True)  # Assertion Consumer Service URL
    sp_sls_url = Column(String(512), nullable=True)  # Single Logout Service URL
    sp_valid_until = Column(String(50), nullable=True)  # Metadata validity period in ISO format

    # Identity Provider (IdP) Configuration
    idp_entity_id = Column(String(512), nullable=True)
    idp_sso_url = Column(String(512), nullable=True)  # Single Sign-On URL
    idp_sls_url = Column(String(512), nullable=True)  # Single Logout Service URL
    idp_x509_cert = Column(Text, nullable=True)  # IdP X.509 Certificate

    # Organization Information (for metadata)
    org_name = Column(String(255), nullable=True)
    org_display_name = Column(String(255), nullable=True)
    org_url = Column(String(512), nullable=True)
    technical_contact_email = Column(String(255), nullable=True)

    # Attribute Mapping (SAML attributes to user fields)
    # Stored as JSON: {"saml_attribute": "user_field", ...}
    # Example: {"email": "email", "givenName": "first_name", "sn": "last_name", "employeeNumber": "id_number"}
    attribute_mapping = Column(JSON, nullable=True)

    # Auto-provisioning settings
    auto_provision_users = Column(Boolean, default=False, nullable=False)
    default_user_role_is_admin = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SAMLConfiguration(id={self.id}, enabled={self.enabled}, sp_entity_id={self.sp_entity_id})>"


class AppVersion(Base):
    """Application version tracking for database upgrades."""
    __tablename__ = "app_version"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(20), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    applied_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<AppVersion(version={self.version}, applied_at={self.applied_at})>"

