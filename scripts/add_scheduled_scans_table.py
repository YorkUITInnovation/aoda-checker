"""Add scheduled_scans table to the database."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.database.session import engine


async def add_scheduled_scans_table():
    """Add the scheduled_scans table to the database."""

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS scheduled_scans (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        start_url VARCHAR(2048) NOT NULL,
        max_pages INT NOT NULL DEFAULT 50,
        max_depth INT NOT NULL DEFAULT 3,
        same_domain_only INT NOT NULL DEFAULT 1,
        scan_mode VARCHAR(20) NOT NULL DEFAULT 'aoda',
        frequency ENUM('daily', 'weekly', 'monthly', 'yearly') NOT NULL,
        schedule_time VARCHAR(5) NOT NULL,
        day_of_week INT DEFAULT NULL,
        day_of_month INT DEFAULT NULL,
        month_of_year INT DEFAULT NULL,
        email_notifications BOOLEAN NOT NULL DEFAULT TRUE,
        notify_on_violations BOOLEAN NOT NULL DEFAULT TRUE,
        notify_on_errors BOOLEAN NOT NULL DEFAULT TRUE,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        last_run DATETIME DEFAULT NULL,
        next_run DATETIME DEFAULT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        INDEX idx_user_id (user_id),
        INDEX idx_is_active (is_active),
        INDEX idx_next_run (next_run)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """

    async with engine.begin() as conn:
        print("Creating scheduled_scans table...")
        await conn.execute(text(create_table_sql))
        print("✓ scheduled_scans table created successfully")


async def main():
    """Run the migration."""
    try:
        await add_scheduled_scans_table()
        print("\n✓ Migration completed successfully!")
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

