"""
Migration: Add user_check_configurations table for per-user check settings.

This allows each user to have their own check configuration preferences.
"""
import asyncio
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.database import get_db_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    """Add user_check_configurations table."""
    logger.info("🔄 Running migration: Add user_check_configurations table")

    async with get_db_session() as db:
        # Create user_check_configurations table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS user_check_configurations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            check_id VARCHAR(128) NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            severity ENUM('error', 'warning', 'alert', 'disabled') NOT NULL DEFAULT 'error',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            
            UNIQUE KEY unique_user_check (user_id, check_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (check_id) REFERENCES check_configurations(check_id) ON DELETE CASCADE,
            INDEX idx_user_id (user_id),
            INDEX idx_check_id (check_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        await db.execute(text(create_table_sql))
        await db.commit()

        logger.info("✅ user_check_configurations table created successfully")

        # Check if table was created
        check_sql = """
        SELECT COUNT(*) as count
        FROM information_schema.tables 
        WHERE table_schema = DATABASE()
        AND table_name = 'user_check_configurations';
        """
        result = await db.execute(text(check_sql))
        count = result.scalar()

        if count > 0:
            logger.info("✅ Migration completed successfully!")
        else:
            logger.error("❌ Table was not created!")


if __name__ == "__main__":
    asyncio.run(migrate())

