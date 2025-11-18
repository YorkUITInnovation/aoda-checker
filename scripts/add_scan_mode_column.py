#!/usr/bin/env python3
"""
Migration script to add scan_mode column to scans table.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.database.session import get_db_session


async def add_scan_mode_column():
    """Add scan_mode column to scans table."""
    async with get_db_session() as db:
        try:
            # Check if column already exists
            result = await db.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'scans' 
                AND COLUMN_NAME = 'scan_mode'
            """))
            row = result.fetchone()
            
            if row[0] > 0:
                print("✓ Column 'scan_mode' already exists in 'scans' table")
                return
            
            # Add the column
            print("Adding 'scan_mode' column to 'scans' table...")
            await db.execute(text("""
                ALTER TABLE scans 
                ADD COLUMN scan_mode VARCHAR(20) NOT NULL DEFAULT 'aoda'
            """))
            await db.commit()
            
            print("✓ Successfully added 'scan_mode' column to 'scans' table")
            print("  Default value: 'aoda'")
            
        except Exception as e:
            print(f"✗ Error adding column: {e}")
            await db.rollback()
            raise


async def main():
    """Run the migration."""
    print("=" * 60)
    print("Database Migration: Add scan_mode Column")
    print("=" * 60)
    
    try:
        await add_scan_mode_column()
        print("\n✓ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

