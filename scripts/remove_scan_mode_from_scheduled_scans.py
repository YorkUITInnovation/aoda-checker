"""Remove scan_mode column from scheduled_scans table."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.database.session import engine


async def remove_scan_mode_column():
    """Remove the scan_mode column from scheduled_scans table."""

    # Check if column exists first
    check_column_sql = """
    SELECT COUNT(*) as count
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'scheduled_scans' 
    AND COLUMN_NAME = 'scan_mode';
    """

    remove_column_sql = """
    ALTER TABLE scheduled_scans DROP COLUMN scan_mode;
    """

    async with engine.begin() as conn:
        # Check if column exists
        result = await conn.execute(text(check_column_sql))
        row = result.fetchone()

        if row and row[0] > 0:
            print("Removing scan_mode column from scheduled_scans table...")
            await conn.execute(text(remove_column_sql))
            print("✓ scan_mode column removed successfully")
            print("✓ Scheduled scans will now use user's check configuration from My Checks")
        else:
            print("✓ scan_mode column does not exist (already removed or never existed)")


async def main():
    """Run the migration."""
    try:
        await remove_scan_mode_column()
        print("\n✓ Migration completed successfully!")
        print("\nNote: Scheduled scans now use your check configuration from 'My Checks'.")
        print("Make sure to configure your checks at /checks before creating scheduled scans.")
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

