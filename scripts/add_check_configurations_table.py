"""Migration script to add check_configurations table."""
import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db_session
from src.database.models import Base, CheckConfiguration
from src.database.check_repository import CheckConfigRepository
from sqlalchemy import text


async def migrate():
    """Run the migration."""
    print("🔄 Running migration: Add check_configurations table")
    
    async with get_db_session() as db:
        # Import the engine
        from src.database.session import engine

        # Create the check_configurations table
        print("📋 Creating check_configurations table...")
        async with engine.begin() as conn:
            # Create table using raw SQL to avoid issues with existing tables
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
        
        print("✅ Table created successfully")
        
        # Initialize with default checks
        print("📦 Initializing default check configurations...")
        repo = CheckConfigRepository(db)
        await repo.initialize_default_checks()
        print("✅ Default checks initialized")
    
    print("🎉 Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())

