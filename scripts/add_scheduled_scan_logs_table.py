"""Add scheduled_scan_logs table to the database."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.database.session import engine


async def add_scheduled_scan_logs_table():
    """Add the scheduled_scan_logs table to the database."""

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS scheduled_scan_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        scheduled_scan_id INT NOT NULL,
        user_id INT NOT NULL,
        start_url VARCHAR(2048) NOT NULL,
        status ENUM('success', 'failed') NOT NULL,
        scan_id VARCHAR(36) DEFAULT NULL,
        pages_scanned INT DEFAULT 0,
        total_violations INT DEFAULT 0,
        error_message TEXT DEFAULT NULL,
        executed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        duration_seconds INT DEFAULT NULL,
        email_sent BOOLEAN NOT NULL DEFAULT FALSE,
        INDEX idx_scheduled_scan_id (scheduled_scan_id),
        INDEX idx_user_id (user_id),
        INDEX idx_executed_at (executed_at),
        FOREIGN KEY (scheduled_scan_id) REFERENCES scheduled_scans(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """

    async with engine.begin() as conn:
        print("Creating scheduled_scan_logs table...")
        await conn.execute(text(create_table_sql))
        print("✓ scheduled_scan_logs table created successfully")


async def main():
    """Run the migration."""
    try:
        await add_scheduled_scan_logs_table()
        print("\n✓ Migration completed successfully!")
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

