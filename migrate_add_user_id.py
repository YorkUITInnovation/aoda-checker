"""Add user_id column to scans table for authentication."""
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from src.config import settings


async def migrate_scans_add_user_id():
    """Add user_id column to scans table."""
    print("Adding user_id column to scans table...")
    
    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_pre_ping=True
    )
    
    try:
        async with engine.begin() as conn:
            # Check if user_id column already exists
            result = await conn.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = 'aoda_checker'
                AND TABLE_NAME = 'scans'
                AND COLUMN_NAME = 'user_id'
            """))
            row = result.fetchone()
            
            if row and row[0] > 0:
                print("✅ user_id column already exists in scans table")
                return
            
            # Check if users table exists
            result = await conn.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = 'aoda_checker'
                AND TABLE_NAME = 'users'
            """))
            row = result.fetchone()
            
            if not row or row[0] == 0:
                print("❌ Error: users table does not exist")
                print("   Please run init_auth.py first to create the users table")
                sys.exit(1)
            
            # Get the admin user ID (or create a system user)
            result = await conn.execute(text("""
                SELECT id FROM users WHERE username = 'admin' LIMIT 1
            """))
            admin_row = result.fetchone()
            
            if not admin_row:
                print("❌ Error: admin user does not exist")
                print("   Please run init_auth.py first to create the admin user")
                sys.exit(1)
            
            admin_id = admin_row[0]
            print(f"✅ Found admin user with ID: {admin_id}")
            
            # Add user_id column (nullable first, then update, then make not null)
            print("📝 Adding user_id column to scans table...")
            await conn.execute(text("""
                ALTER TABLE scans
                ADD COLUMN user_id INT NULL
            """))
            print("✅ Column added")
            
            # Update existing scans to belong to admin user
            print(f"📝 Assigning existing scans to admin user (ID: {admin_id})...")
            result = await conn.execute(text(f"""
                UPDATE scans
                SET user_id = {admin_id}
                WHERE user_id IS NULL
            """))
            print(f"✅ Updated {result.rowcount} existing scans")
            
            # Make user_id NOT NULL
            print("📝 Making user_id column NOT NULL...")
            await conn.execute(text("""
                ALTER TABLE scans
                MODIFY COLUMN user_id INT NOT NULL
            """))
            print("✅ Column is now NOT NULL")
            
            # Add index on user_id
            print("📝 Adding index on user_id...")
            await conn.execute(text("""
                ALTER TABLE scans
                ADD INDEX idx_user_id (user_id)
            """))
            print("✅ Index added")
            
            # Add foreign key constraint
            print("📝 Adding foreign key constraint...")
            await conn.execute(text("""
                ALTER TABLE scans
                ADD CONSTRAINT fk_scans_user_id
                FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE
            """))
            print("✅ Foreign key constraint added")
            
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print(f"\nAll existing scans have been assigned to admin user (ID: {admin_id})")
        print("New scans will be automatically assigned to the creating user.")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(migrate_scans_add_user_id())
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

