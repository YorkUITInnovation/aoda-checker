"""Test if check_configurations table exists and has data."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.database.session import engine


async def test():
    """Test table existence and data."""
    try:
        async with engine.begin() as conn:
            # Check if table exists
            result = await conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = 'aoda_checker' 
                AND table_name = 'check_configurations'
            """))
            table_exists = result.scalar() > 0
            
            if table_exists:
                print("✅ check_configurations table EXISTS")
                
                # Count rows
                result = await conn.execute(text("SELECT COUNT(*) FROM check_configurations"))
                row_count = result.scalar()
                print(f"📊 Table has {row_count} rows")
                
                if row_count > 0:
                    # Show sample data
                    result = await conn.execute(text("""
                        SELECT check_id, check_name, enabled, severity 
                        FROM check_configurations 
                        LIMIT 5
                    """))
                    print("\n📋 Sample checks:")
                    for row in result:
                        print(f"   - {row[0]}: {row[1]} (enabled={row[2]}, severity={row[3]})")
            else:
                print("❌ check_configurations table DOES NOT EXIST")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test())

