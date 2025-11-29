"""Simple migration script to add check_configurations table."""
import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.database.session import engine
from src.database.check_repository import CheckConfigRepository, get_default_check_configurations
from src.database.models import CheckConfiguration


async def migrate():
    """Run the migration."""
    print("🔄 Starting migration: Add check_configurations table", flush=True)
    
    try:
        # Create the check_configurations table using raw SQL
        print("📋 Creating check_configurations table...", flush=True)
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS check_configurations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    check_id VARCHAR(128) UNIQUE NOT NULL,
                    check_name VARCHAR(255) NOT NULL,
                    description TEXT,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    severity ENUM('error', 'warning', 'alert', 'disabled') NOT NULL DEFAULT 'error',
                    wcag_criterion VARCHAR(128),
                    wcag_level VARCHAR(10),
                    aoda_required BOOLEAN NOT NULL DEFAULT FALSE,
                    wcag21_only BOOLEAN NOT NULL DEFAULT FALSE,
                    check_type VARCHAR(50) NOT NULL DEFAULT 'axe',
                    help_url VARCHAR(512),
                    tags JSON,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_check_id (check_id),
                    INDEX idx_enabled (enabled)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
        
        print("✅ Table created successfully", flush=True)
        
        # Initialize with default checks
        print("📦 Initializing default check configurations...", flush=True)
        
        # Use a new session for inserts
        from src.database import get_db_session
        async with get_db_session() as db:
            repo = CheckConfigRepository(db)
            
            # Get defaults
            defaults = get_default_check_configurations()
            print(f"   Found {len(defaults)} default checks to initialize", flush=True)
            
            # Insert each check
            inserted_count = 0
            for check_data in defaults:
                try:
                    existing = await repo.get_check_by_id(check_data["check_id"])
                    if not existing:
                        await repo.create_check(**check_data)
                        inserted_count += 1
                except Exception as e:
                    print(f"   ⚠️  Warning: Could not insert {check_data['check_id']}: {e}", flush=True)
            
            print(f"✅ Initialized {inserted_count} checks", flush=True)
        
        print("🎉 Migration completed successfully!", flush=True)
        
    except Exception as e:
        print(f"❌ Migration failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(migrate())

