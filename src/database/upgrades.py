"""Database upgrade registry and definitions.

This module defines all database upgrades in chronological order.
Each upgrade is applied when the application version is higher than the database version.
"""
from typing import List, Dict, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseUpgrade:
    """Represents a single database upgrade."""

    def __init__(
        self,
        version: str,
        description: str,
        upgrade_func: Callable,
        script_name: Optional[str] = None
    ):
        """Initialize upgrade definition.

        Args:
            version: Target version (e.g., "1.1.0")
            description: Human-readable description of what this upgrade does
            upgrade_func: Async function that performs the upgrade
            script_name: Optional reference to the original script file
        """
        self.version = version
        self.description = description
        self.upgrade_func = upgrade_func
        self.script_name = script_name

    async def apply(self, db_session):
        """Apply this upgrade.

        Args:
            db_session: AsyncSession database connection

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Applying upgrade to version {self.version}: {self.description}")
            await self.upgrade_func(db_session)
            logger.info(f"✓ Successfully applied upgrade to version {self.version}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to apply upgrade to version {self.version}: {str(e)}")
            raise

    def __repr__(self):
        return f"<DatabaseUpgrade(version={self.version}, description={self.description})>"


# ============================================================================
# Upgrade Functions
# ============================================================================

async def upgrade_to_1_1_0(db_session):
    """Upgrade to version 1.1.0: Add SAML sp_valid_until field."""
    from sqlalchemy import text

    # Check if column already exists
    result = await db_session.execute(text("""
        SELECT COUNT(*) as count 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = 'saml_configurations' 
        AND COLUMN_NAME = 'sp_valid_until'
    """))
    row = result.fetchone()

    if row[0] > 0:
        logger.info("Column 'sp_valid_until' already exists, skipping")
        return

    # Add the column
    await db_session.execute(text("""
        ALTER TABLE saml_configurations 
        ADD COLUMN sp_valid_until VARCHAR(50) NULL
    """))
    await db_session.commit()
    logger.info("Added sp_valid_until column to saml_configurations table")


# ============================================================================
# Upgrade Registry
# ============================================================================

# All upgrades in chronological order
# Add new upgrades to the end of this list
UPGRADES: List[DatabaseUpgrade] = [
    DatabaseUpgrade(
        version="1.1.0",
        description="Add SAML validUntil metadata field",
        upgrade_func=upgrade_to_1_1_0,
        script_name="add_sp_valid_until_column.py"
    ),
    # Future upgrades go here:
    # DatabaseUpgrade(
    #     version="1.2.0",
    #     description="Add new feature X",
    #     upgrade_func=upgrade_to_1_2_0,
    #     script_name="add_feature_x.py"
    # ),
]


def get_upgrades_needed(current_db_version: str, target_version: str) -> List[DatabaseUpgrade]:
    """Get list of upgrades needed to go from current to target version.

    Args:
        current_db_version: Current database version (e.g., "1.0.0")
        target_version: Target application version (e.g., "1.2.0")

    Returns:
        List of DatabaseUpgrade objects that need to be applied
    """
    from packaging import version

    current = version.parse(current_db_version)
    target = version.parse(target_version)

    if current >= target:
        return []

    # Get all upgrades between current and target
    needed_upgrades = [
        upgrade for upgrade in UPGRADES
        if current < version.parse(upgrade.version) <= target
    ]

    # Sort by version to ensure correct order
    needed_upgrades.sort(key=lambda u: version.parse(u.version))

    return needed_upgrades


def get_latest_upgrade_version() -> str:
    """Get the latest upgrade version defined in the registry.

    Returns:
        Version string of the latest upgrade, or "1.0.0" if no upgrades
    """
    if not UPGRADES:
        return "1.0.0"

    from packaging import version
    return max(upgrade.version for upgrade in UPGRADES, key=version.parse)

