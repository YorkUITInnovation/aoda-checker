"""Database upgrade runner.

Handles automatic database upgrades when application version is higher than database version.
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from datetime import datetime

from src.database.models import AppVersion
from src.database.upgrades import get_upgrades_needed, UPGRADES
from src.config import Settings

logger = logging.getLogger(__name__)


class UpgradeRunner:
    """Manages database schema upgrades."""

    def __init__(self, db_session: AsyncSession, app_version: str):
        """Initialize upgrade runner.

        Args:
            db_session: Database session
            app_version: Current application version
        """
        self.db_session = db_session
        self.app_version = app_version

    async def ensure_version_table_exists(self):
        """Ensure the app_version table exists."""
        try:
            # Try to create the table if it doesn't exist
            await self.db_session.execute(text("""
                CREATE TABLE IF NOT EXISTS app_version (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    version VARCHAR(20) NOT NULL UNIQUE,
                    description VARCHAR(255),
                    applied_at DATETIME NOT NULL,
                    INDEX idx_version (version)
                )
            """))
            await self.db_session.commit()
        except Exception as e:
            logger.warning(f"Error ensuring version table exists: {e}")
            await self.db_session.rollback()

    async def get_current_db_version(self) -> str:
        """Get the current database version.

        Returns:
            Current database version string, or "1.0.0" if not set
        """
        try:
            # Get the latest version from the database
            result = await self.db_session.execute(
                select(AppVersion).order_by(AppVersion.applied_at.desc()).limit(1)
            )
            version_record = result.scalar_one_or_none()

            if version_record:
                return version_record.version
            else:
                # No version recorded, assume fresh install at 1.0.0
                return "1.0.0"
        except Exception as e:
            logger.warning(f"Error getting database version: {e}")
            # If table doesn't exist or error, assume 1.0.0
            return "1.0.0"

    async def record_version(self, version: str, description: str):
        """Record a version upgrade in the database.

        Args:
            version: Version that was applied
            description: Description of the upgrade
        """
        try:
            version_record = AppVersion(
                version=version,
                description=description,
                applied_at=datetime.utcnow()
            )
            self.db_session.add(version_record)
            await self.db_session.commit()
            logger.info(f"Recorded version {version} in database")
        except Exception as e:
            logger.error(f"Error recording version: {e}")
            await self.db_session.rollback()
            raise

    async def needs_upgrade(self) -> bool:
        """Check if database needs upgrading.

        Returns:
            True if upgrade needed, False otherwise
        """
        await self.ensure_version_table_exists()
        current_version = await self.get_current_db_version()

        from packaging import version
        return version.parse(current_version) < version.parse(self.app_version)

    async def run_upgrades(self) -> dict:
        """Run all pending database upgrades.

        Returns:
            Dictionary with upgrade results:
            {
                'success': bool,
                'upgrades_applied': int,
                'current_version': str,
                'target_version': str,
                'errors': list
            }
        """
        result = {
            'success': False,
            'upgrades_applied': 0,
            'current_version': '',
            'target_version': self.app_version,
            'errors': []
        }

        try:
            # Ensure version table exists
            await self.ensure_version_table_exists()

            # Get current database version
            current_version = await self.get_current_db_version()
            result['current_version'] = current_version

            logger.info(f"Database version: {current_version}, Application version: {self.app_version}")

            # Check if upgrade needed
            from packaging import version
            if version.parse(current_version) >= version.parse(self.app_version):
                logger.info("Database is up to date, no upgrades needed")
                result['success'] = True
                return result

            # Get upgrades to apply
            upgrades_to_apply = get_upgrades_needed(current_version, self.app_version)

            if not upgrades_to_apply:
                logger.info("No upgrades defined between versions")
                result['success'] = True
                return result

            logger.info(f"Found {len(upgrades_to_apply)} upgrade(s) to apply")

            # Apply each upgrade in order
            for upgrade in upgrades_to_apply:
                try:
                    logger.info(f"Applying upgrade: {upgrade.version} - {upgrade.description}")

                    # Apply the upgrade
                    await upgrade.apply(self.db_session)

                    # Record the version
                    await self.record_version(upgrade.version, upgrade.description)

                    result['upgrades_applied'] += 1
                    logger.info(f"✓ Successfully upgraded to version {upgrade.version}")

                except Exception as e:
                    error_msg = f"Failed to apply upgrade {upgrade.version}: {str(e)}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
                    # Don't continue with remaining upgrades if one fails
                    raise

            result['success'] = True
            logger.info(f"✓ All upgrades completed successfully. Database now at version {self.app_version}")

        except Exception as e:
            error_msg = f"Upgrade process failed: {str(e)}"
            logger.error(error_msg)
            result['errors'].append(error_msg)
            result['success'] = False
            await self.db_session.rollback()

        return result


async def check_and_run_upgrades(db_session: AsyncSession, app_version: str) -> dict:
    """Check if upgrades are needed and run them.

    This is the main entry point for the upgrade system.

    Args:
        db_session: Database session
        app_version: Current application version

    Returns:
        Dictionary with upgrade results
    """
    runner = UpgradeRunner(db_session, app_version)

    # Check if upgrade needed
    needs_upgrade = await runner.needs_upgrade()

    if not needs_upgrade:
        return {
            'success': True,
            'upgrades_applied': 0,
            'current_version': await runner.get_current_db_version(),
            'target_version': app_version,
            'errors': []
        }

    # Run upgrades
    logger.info("Database upgrade needed, starting upgrade process...")
    result = await runner.run_upgrades()

    return result

