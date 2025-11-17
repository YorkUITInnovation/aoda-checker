"""Initialize authentication tables and create default admin user."""
import asyncio
import sys
import time
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from src.database.models import Base, User
from src.database.user_repository import UserRepository
from src.config import settings


async def wait_for_db(engine, max_retries=30):
    """Wait for database to be ready."""
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            print("✅ Database connection established!")
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⏳ Waiting for database... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(2)
            else:
                print(f"❌ Failed to connect to database after {max_retries} attempts")
                raise
    return False


async def init_auth():
    """Initialize authentication system."""
    print("Initializing authentication system...")
    
    # Create async engine with connection pool settings
    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600    # Recycle connections after 1 hour
    )
    
    try:
        # Create all tables
        print("Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✅ Tables created successfully!")

        # Create session
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        # Check if admin user exists
        async with async_session() as session:
            user_repo = UserRepository(session)

            try:
                admin_user = await user_repo.get_user_by_username("admin")

                if admin_user:
                    print("\n⚠️  Admin user already exists!")
                    print(f"   Username: {admin_user.username}")
                    print(f"   Created: {admin_user.created_at}")
                    return
            except Exception as e:
                print(f"⚠️  Could not check for existing admin user: {e}")
                print("   Attempting to create admin user anyway...")

            # Create default admin user
            print("\nCreating default admin user...")
            print("=" * 50)
            print("⚠️  IMPORTANT: Change this password after first login!")
            print("=" * 50)

            try:
                admin = await user_repo.create_user(
                    username="admin",
                    password="admin123",  # Default password - MUST BE CHANGED
                    email="admin@example.com",
                    full_name="System Administrator",
                    is_admin=True,
                    auth_method="manual"
                )

                print("\n✅ Default admin user created successfully!")
                print(f"\n   Username: {admin.username}")
                print(f"   Password: admin123")
                print(f"   Email: {admin.email}")
                print("\n" + "=" * 50)
                print("⚠️  SECURITY WARNING:")
                print("   Please login and change the default password immediately!")
                print("   Go to: http://localhost:8080/login")
                print("=" * 50)
            except Exception as e:
                if "Duplicate entry" in str(e) or "already exists" in str(e).lower():
                    print("\n⚠️  Admin user already exists (caught during creation)")
                else:
                    raise

    finally:
        # Always close the engine
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(init_auth())
        print("\n✅ Authentication initialization complete!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error initializing authentication: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

