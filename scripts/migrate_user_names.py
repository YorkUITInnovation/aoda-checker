#!/usr/bin/env python3
"""
Migration: Add first_name, last_name, id_number to users table and migrate full_name data.

This migration:
1. Adds first_name, last_name, and id_number columns to users table
2. Migrates data from full_name to first_name and last_name (splitting on space)
3. Drops the full_name column
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.database.session import engine


async def migrate():
    """Run the migration."""
    print("🔄 Running migration: Update users table structure")

    async with engine.begin() as conn:
        try:
            # Step 1: Add new columns
            print("📝 Step 1: Adding new columns (first_name, last_name, id_number)...")

            # Check if columns already exist
            result = await conn.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'users'
                AND COLUMN_NAME = 'first_name'
            """))
            first_name_exists = result.scalar() > 0

            if not first_name_exists:
                await conn.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN first_name VARCHAR(255) NULL AFTER username,
                    ADD COLUMN last_name VARCHAR(255) NULL AFTER first_name,
                    ADD COLUMN id_number VARCHAR(100) NULL AFTER last_name
                """))
                print("✅ New columns added successfully")
            else:
                print("⚠️  Columns already exist, skipping creation")

            # Step 2: Migrate data from full_name to first_name and last_name
            print("📝 Step 2: Migrating data from full_name to first_name and last_name...")

            # Check if full_name column exists
            result = await conn.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'users'
                AND COLUMN_NAME = 'full_name'
            """))
            full_name_exists = result.scalar() > 0

            if full_name_exists:
                # Get all users with full_name data
                result = await conn.execute(text("""
                    SELECT id, full_name FROM users WHERE full_name IS NOT NULL
                """))
                users = result.fetchall()

                print(f"   Found {len(users)} users with full_name data")

                # Update each user
                for user in users:
                    user_id = user[0]
                    full_name = user[1]

                    if full_name:
                        # Split on first space
                        parts = full_name.split(' ', 1)
                        first_name = parts[0] if len(parts) > 0 else ''
                        last_name = parts[1] if len(parts) > 1 else ''

                        await conn.execute(
                            text("""
                                UPDATE users 
                                SET first_name = :first_name, last_name = :last_name
                                WHERE id = :user_id
                            """),
                            {"first_name": first_name, "last_name": last_name, "user_id": user_id}
                        )
                        print(f"   ✓ Migrated: '{full_name}' → first_name: '{first_name}', last_name: '{last_name}'")

                print("✅ Data migration completed")

                # Step 3: Drop full_name column
                print("📝 Step 3: Dropping full_name column...")
                await conn.execute(text("ALTER TABLE users DROP COLUMN full_name"))
                print("✅ full_name column dropped")
            else:
                print("⚠️  full_name column doesn't exist, skipping migration")

            print("\n✅ Migration completed successfully!")
            print("\n📊 Summary:")
            print("   • Added: first_name, last_name, id_number columns")
            print("   • Migrated: full_name data to first_name and last_name")
            print("   • Removed: full_name column")

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(migrate())

