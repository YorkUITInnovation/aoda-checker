"""Create database tables for AODA Compliance Checker.

This script creates the MySQL database schema.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import init_db
from src.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Initialize database tables."""
    logger.info(f"Connecting to database: {settings.database_url.split('@')[1]}")

    try:
        await init_db()
        logger.info("✅ Database tables created successfully!")
        logger.info("")
        logger.info("Tables created:")
        logger.info("  - scans: Stores scan metadata and summary")
        logger.info("  - page_scans: Stores individual page scan results")
        logger.info("  - violations: Stores accessibility violations found")

    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

