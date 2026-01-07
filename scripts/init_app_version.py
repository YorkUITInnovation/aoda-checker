#!/usr/bin/env python3
"""
Initialize the app_version table and set to 1.0.0 for existing installations.

This script should be run once on existing installations before upgrading to v1.1.0+.
New installations will automatically have this table created.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.database.session import get_db_session
from datetime import datetime


async def initialize_app_version_table():
    """Create app_version table and set initial version to 1.0.0."""
    async with get_db_session() as db:
        try:
            print("=" * 60)
            print("Initializing App Version Tracking System")
            print("=" * 60)

            # Create the app_version table
            print("\n1. Creating app_version table...")
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS app_version (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    version VARCHAR(20) NOT NULL UNIQUE,
                    description VARCHAR(255),
                    applied_at DATETIME NOT NULL,
                    INDEX idx_version (version)
                )
            """))
            await db.commit()
            print("✓ Table created successfully")

            # Check if we already have a version recorded
            result = await db.execute(text("SELECT COUNT(*) as count FROM app_version"))
            row = result.fetchone()

            if row[0] > 0:
                print("\n✓ App version table already initialized")
                result = await db.execute(text("SELECT version, applied_at FROM app_version ORDER BY applied_at DESC LIMIT 1"))
                version_row = result.fetchone()
                print(f"  Current version: {version_row[0]}")
                print(f"  Last updated: {version_row[1]}")
                return

            # Insert initial version 1.0.0
            print("\n2. Setting initial version to 1.0.0...")
            await db.execute(text("""
                INSERT INTO app_version (version, description, applied_at)
                VALUES (:version, :description, :applied_at)
            """), {
                'version': '1.0.0',
                'description': 'Initial version',
                'applied_at': datetime.utcnow()
            })
            await db.commit()
            print("✓ Initial version set to 1.0.0")

            print("\n" + "=" * 60)
            print("✓ App version tracking system initialized successfully!")
            print("=" * 60)
            print("\nNext steps:")
            print("- The system will now automatically track database schema versions")
            print("- When an admin logs in, any pending upgrades will be applied")
            print("- You can check the app_version table to see upgrade history")

        except Exception as e:
            print(f"\n✗ Error initializing app version table: {e}")
            await db.rollback()
            raise


async def main():
    """Run the initialization."""
    try:
        await initialize_app_version_table()

    except Exception as e:
        print(f"\n✗ Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

