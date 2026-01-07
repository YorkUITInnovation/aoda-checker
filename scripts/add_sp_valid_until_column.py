#!/usr/bin/env python3
"""
Migration script to add sp_valid_until column to saml_configurations table.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.database.session import get_db_session


async def add_sp_valid_until_column():
    """Add sp_valid_until column to saml_configurations table."""
    async with get_db_session() as db:
        try:
            # Check if column already exists
            result = await db.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'saml_configurations' 
                AND COLUMN_NAME = 'sp_valid_until'
            """))
            row = result.fetchone()

            if row[0] > 0:
                print("✓ Column 'sp_valid_until' already exists in 'saml_configurations' table")
                return

            # Add the column
            print("Adding 'sp_valid_until' column to 'saml_configurations' table...")
            await db.execute(text("""
                ALTER TABLE saml_configurations 
                ADD COLUMN sp_valid_until VARCHAR(50) NULL
            """))
            await db.commit()

            print("✓ Successfully added 'sp_valid_until' column to 'saml_configurations' table")
            print("  Column type: VARCHAR(50), nullable")
            print("  This field stores the metadata validity period in ISO 8601 format")

        except Exception as e:
            print(f"✗ Error adding column: {e}")
            await db.rollback()
            raise


async def main():
    """Run the migration."""
    print("=" * 60)
    print("Database Migration: Add sp_valid_until Column")
    print("=" * 60)

    try:
        await add_sp_valid_until_column()
        print("\n✓ Migration completed successfully!")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

