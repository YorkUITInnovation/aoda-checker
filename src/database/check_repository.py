"""Repository for check configuration operations."""
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.exc import IntegrityError

from src.database.models import CheckConfiguration, CheckSeverity, UserCheckConfiguration


class CheckConfigRepository:
    """Repository for managing check configurations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_checks(self) -> List[CheckConfiguration]:
        """Get all check configurations."""
        result = await self.db.execute(select(CheckConfiguration))
        return list(result.scalars().all())

    async def get_enabled_checks(self) -> List[CheckConfiguration]:
        """Get only enabled check configurations."""
        result = await self.db.execute(
            select(CheckConfiguration).where(CheckConfiguration.enabled == True)
        )
        return list(result.scalars().all())

    async def get_check_by_id(self, check_id: str) -> Optional[CheckConfiguration]:
        """Get a specific check configuration by ID."""
        result = await self.db.execute(
            select(CheckConfiguration).where(CheckConfiguration.check_id == check_id)
        )
        return result.scalar_one_or_none()

    async def create_check(
        self,
        check_id: str,
        check_name: str,
        description: Optional[str] = None,
        enabled: bool = True,
        severity: CheckSeverity = CheckSeverity.ERROR,
        wcag_criterion: Optional[str] = None,
        wcag_level: Optional[str] = None,
        aoda_required: bool = False,
        wcag21_only: bool = False,
        check_type: str = "axe",
        help_url: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> CheckConfiguration:
        """Create a new check configuration."""
        check = CheckConfiguration(
            check_id=check_id,
            check_name=check_name,
            description=description,
            enabled=enabled,
            severity=severity,
            wcag_criterion=wcag_criterion,
            wcag_level=wcag_level,
            aoda_required=aoda_required,
            wcag21_only=wcag21_only,
            check_type=check_type,
            help_url=help_url,
            tags=tags or []
        )
        self.db.add(check)
        await self.db.commit()
        await self.db.refresh(check)
        return check

    async def update_check(
        self,
        check_id: str,
        enabled: Optional[bool] = None,
        severity: Optional[CheckSeverity] = None
    ) -> Optional[CheckConfiguration]:
        """Update a check configuration."""
        check = await self.get_check_by_id(check_id)
        if not check:
            return None

        if enabled is not None:
            check.enabled = enabled
        if severity is not None:
            check.severity = severity

        await self.db.commit()
        await self.db.refresh(check)
        return check

    async def initialize_default_checks(self):
        """Initialize the database with default check configurations."""
        default_checks = get_default_check_configurations()
        
        for check_data in default_checks:
            existing = await self.get_check_by_id(check_data["check_id"])
            if not existing:
                await self.create_check(**check_data)

    # User-specific check configuration methods

    async def get_user_checks(self, user_id: int) -> List[Dict]:
        """
        Get all checks with user-specific overrides applied.
        Returns list of dicts with check data and user preferences.
        """
        # Get all check configurations
        base_checks = await self.get_all_checks()

        # Get user's overrides
        result = await self.db.execute(
            select(UserCheckConfiguration).where(UserCheckConfiguration.user_id == user_id)
        )
        user_overrides = {uc.check_id: uc for uc in result.scalars().all()}

        # Merge base checks with user overrides
        checks = []
        for check in base_checks:
            user_override = user_overrides.get(check.check_id)
            checks.append({
                "id": check.id,
                "check_id": check.check_id,
                "check_name": check.check_name,
                "description": check.description,
                "enabled": user_override.enabled if user_override else check.enabled,
                "severity": user_override.severity.value if user_override else check.severity.value,
                "wcag_criterion": check.wcag_criterion,
                "wcag_level": check.wcag_level,
                "aoda_required": check.aoda_required,
                "wcag21_only": check.wcag21_only,
                "check_type": check.check_type,
                "help_url": check.help_url,
                "has_user_override": user_override is not None
            })

        return checks

    async def get_enabled_checks_for_user(self, user_id: int) -> List[str]:
        """
        Get list of enabled check IDs for a specific user.
        Returns check_ids that are enabled (considering user overrides).
        """
        checks = await self.get_user_checks(user_id)
        return [check["check_id"] for check in checks if check["enabled"]]

    async def update_user_check(
        self,
        user_id: int,
        check_id: str,
        enabled: Optional[bool] = None,
        severity: Optional[CheckSeverity] = None
    ) -> UserCheckConfiguration:
        """
        Update or create a user-specific check configuration override.
        """
        # Check if override already exists
        result = await self.db.execute(
            select(UserCheckConfiguration).where(
                and_(
                    UserCheckConfiguration.user_id == user_id,
                    UserCheckConfiguration.check_id == check_id
                )
            )
        )
        user_check = result.scalar_one_or_none()

        if user_check:
            # Update existing override
            if enabled is not None:
                user_check.enabled = enabled
            if severity is not None:
                user_check.severity = severity
        else:
            # Create new override
            # First verify the base check exists
            base_check = await self.get_check_by_id(check_id)
            if not base_check:
                raise ValueError(f"Check {check_id} does not exist")

            user_check = UserCheckConfiguration(
                user_id=user_id,
                check_id=check_id,
                enabled=enabled if enabled is not None else base_check.enabled,
                severity=severity if severity is not None else base_check.severity
            )
            self.db.add(user_check)

        await self.db.commit()
        await self.db.refresh(user_check)
        return user_check

    async def reset_user_check(self, user_id: int, check_id: str) -> bool:
        """
        Reset a user's check configuration to default (remove override).
        Returns True if an override was deleted, False if none existed.
        """
        result = await self.db.execute(
            delete(UserCheckConfiguration).where(
                and_(
                    UserCheckConfiguration.user_id == user_id,
                    UserCheckConfiguration.check_id == check_id
                )
            )
        )
        await self.db.commit()
        return result.rowcount > 0

    async def reset_all_user_checks(self, user_id: int) -> int:
        """
        Reset all of a user's check configurations to defaults.
        Returns number of overrides deleted.
        """
        result = await self.db.execute(
            delete(UserCheckConfiguration).where(UserCheckConfiguration.user_id == user_id)
        )
        await self.db.commit()
        return result.rowcount


def get_default_check_configurations() -> List[Dict]:
    """Get the default check configurations."""
    return [
        # Images
        {
            "check_id": "image-alt",
            "check_name": "Images must have alternative text",
            "description": "Ensures <img> elements have alternate text or a role of none or presentation",
            "enabled": True,
            "severity": CheckSeverity.ERROR,
            "wcag_criterion": "1.1.1",
            "wcag_level": "A",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/image-alt",
            "tags": ["cat.text-alternatives", "wcag2a", "wcag111", "section508"]
        },
        {
            "check_id": "spacer-image-alt",
            "check_name": "Decorative spacer images should have empty alt attribute",
            "description": "Ensures decorative spacer images (1px, transparent.gif, spacer images) have alt=\"\" to hide them from screen readers. Spacer images with descriptive alt text are flagged.",
            "enabled": True,
            "severity": CheckSeverity.ERROR,
            "wcag_criterion": "1.1.1",
            "wcag_level": "A",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "custom",
            "help_url": "https://www.w3.org/WAI/WCAG21/Understanding/non-text-content.html",
            "tags": ["cat.text-alternatives", "wcag2a", "wcag111"]
        },
        # Headings
        {
            "check_id": "empty-heading",
            "check_name": "Headings must not be empty",
            "description": "Ensures headings have discernible text",
            "enabled": True,
            "severity": CheckSeverity.ERROR,
            "wcag_criterion": "2.4.6",
            "wcag_level": "AA",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/empty-heading",
            "tags": ["cat.name-role-value", "wcag2aa", "wcag246"]
        },
        {
            "check_id": "heading-order",
            "check_name": "Heading levels should only increase by one",
            "description": "Ensures heading levels are in a sequentially descending order",
            "enabled": True,
            "severity": CheckSeverity.ALERT,
            "wcag_criterion": "1.3.1",
            "wcag_level": "A",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/heading-order",
            "tags": ["cat.semantics", "wcag2a", "wcag131"]
        },
        {
            "check_id": "p-as-heading",
            "check_name": "Bold, italic text and font-size should not be used for styling p elements as headings",
            "description": "Detects paragraphs that look like headings",
            "enabled": True,
            "severity": CheckSeverity.ALERT,
            "wcag_criterion": "1.3.1",
            "wcag_level": "A",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/p-as-heading",
            "tags": ["cat.semantics", "wcag2a", "wcag131"]
        },
        # Contrast
        {
            "check_id": "color-contrast",
            "check_name": "Elements must have sufficient color contrast",
            "description": "Ensures the contrast between foreground and background colors meets WCAG 2 AA contrast ratio thresholds",
            "enabled": True,
            "severity": CheckSeverity.ERROR,
            "wcag_criterion": "1.4.3",
            "wcag_level": "AA",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/color-contrast",
            "tags": ["cat.color", "wcag2aa", "wcag143"]
        },
        {
            "check_id": "color-contrast-enhanced",
            "check_name": "Elements must have sufficient color contrast (enhanced)",
            "description": "Ensures the contrast between foreground and background colors meets WCAG 2 AAA contrast ratio thresholds",
            "enabled": False,
            "severity": CheckSeverity.WARNING,
            "wcag_criterion": "1.4.6",
            "wcag_level": "AAA",
            "aoda_required": False,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/color-contrast-enhanced",
            "tags": ["cat.color", "wcag2aaa", "wcag146"]
        },
        # Frames
        {
            "check_id": "frame-title",
            "check_name": "Frames must have an accessible name",
            "description": "Ensures <iframe> and <frame> elements have an accessible name",
            "enabled": True,
            "severity": CheckSeverity.ERROR,
            "wcag_criterion": "4.1.2",
            "wcag_level": "A",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/frame-title",
            "tags": ["cat.text-alternatives", "wcag2a", "wcag412", "section508"]
        },
        # Noscript
        {
            "check_id": "noscript-element",
            "check_name": "Noscript elements should provide alternative content",
            "description": "Detects noscript elements that may indicate JavaScript dependency",
            "enabled": True,
            "severity": CheckSeverity.ALERT,
            "wcag_criterion": "4.1.2",
            "wcag_level": "A",
            "aoda_required": False,
            "wcag21_only": False,
            "check_type": "custom",
            "help_url": "https://www.w3.org/TR/WCAG20-TECHS/G173.html",
            "tags": ["cat.parsing", "best-practice"]
        },
        # Links
        {
            "check_id": "link-name",
            "check_name": "Links must have discernible text",
            "description": "Ensures links have discernible text",
            "enabled": True,
            "severity": CheckSeverity.ERROR,
            "wcag_criterion": "2.4.4",
            "wcag_level": "A",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/link-name",
            "tags": ["cat.name-role-value", "wcag2a", "wcag244", "section508"]
        },
        # Forms
        {
            "check_id": "label",
            "check_name": "Form elements must have labels",
            "description": "Ensures every form element has a label",
            "enabled": True,
            "severity": CheckSeverity.ERROR,
            "wcag_criterion": "3.3.2",
            "wcag_level": "A",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/label",
            "tags": ["cat.forms", "wcag2a", "wcag332", "section508"]
        },
        # Page structure
        {
            "check_id": "document-title",
            "check_name": "Documents must have a title element",
            "description": "Ensures each HTML document contains a non-empty <title> element",
            "enabled": True,
            "severity": CheckSeverity.ERROR,
            "wcag_criterion": "2.4.2",
            "wcag_level": "A",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/document-title",
            "tags": ["cat.text-alternatives", "wcag2a", "wcag242"]
        },
        {
            "check_id": "html-has-lang",
            "check_name": "HTML element must have a lang attribute",
            "description": "Ensures every HTML document has a lang attribute",
            "enabled": True,
            "severity": CheckSeverity.ERROR,
            "wcag_criterion": "3.1.1",
            "wcag_level": "A",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/html-has-lang",
            "tags": ["cat.language", "wcag2a", "wcag311"]
        },
        {
            "check_id": "bypass",
            "check_name": "Page must have a skip link",
            "description": "Ensures each page has at least one mechanism for a keyboard user to bypass navigation",
            "enabled": True,
            "severity": CheckSeverity.ERROR,
            "wcag_criterion": "2.4.1",
            "wcag_level": "A",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/bypass",
            "tags": ["cat.keyboard", "wcag2a", "wcag241", "section508"]
        },
        # ARIA
        {
            "check_id": "aria-allowed-attr",
            "check_name": "ARIA attributes must be allowed for element's role",
            "description": "Ensures ARIA attributes are allowed for an element's role",
            "enabled": True,
            "severity": CheckSeverity.ERROR,
            "wcag_criterion": "4.1.2",
            "wcag_level": "A",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/aria-allowed-attr",
            "tags": ["cat.aria", "wcag2a", "wcag412"]
        },
        {
            "check_id": "aria-required-attr",
            "check_name": "ARIA roles must have required attributes",
            "description": "Ensures elements with ARIA roles have all required ARIA attributes",
            "enabled": True,
            "severity": CheckSeverity.ERROR,
            "wcag_criterion": "4.1.2",
            "wcag_level": "A",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/aria-required-attr",
            "tags": ["cat.aria", "wcag2a", "wcag412"]
        },
        {
            "check_id": "aria-valid-attr",
            "check_name": "ARIA attributes must be valid",
            "description": "Ensures attributes that begin with aria- are valid ARIA attributes",
            "enabled": True,
            "severity": CheckSeverity.ERROR,
            "wcag_criterion": "4.1.2",
            "wcag_level": "A",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/aria-valid-attr",
            "tags": ["cat.aria", "wcag2a", "wcag412"]
        },
        {
            "check_id": "aria-valid-attr-value",
            "check_name": "ARIA attribute values must be valid",
            "description": "Ensures all ARIA attributes have valid values",
            "enabled": True,
            "severity": CheckSeverity.ERROR,
            "wcag_criterion": "4.1.2",
            "wcag_level": "A",
            "aoda_required": True,
            "wcag21_only": False,
            "check_type": "axe",
            "help_url": "https://dequeuniversity.com/rules/axe/4.4/aria-valid-attr-value",
            "tags": ["cat.aria", "wcag2a", "wcag412"]
        },
    ]

