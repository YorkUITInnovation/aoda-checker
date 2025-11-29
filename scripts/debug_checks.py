"""Debug script to check what's in the database and what the API returns."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.check_repository import CheckConfigRepository
from src.database import get_db_session


async def debug_checks():
    """Debug check configurations."""
    print("="*60)
    print("DEBUG: Check Configurations")
    print("="*60)
    
    async with get_db_session() as db:
        repo = CheckConfigRepository(db)
        checks = await repo.get_all_checks()
        
        print(f"\nTotal checks in database: {len(checks)}\n")
        
        print("List of all checks:")
        print("-" * 60)
        for i, check in enumerate(checks, 1):
            print(f"{i:2d}. {check.check_id:30s} | {check.check_name}")
            print(f"    Enabled: {check.enabled}, Severity: {check.severity.value if check.severity else 'None'}")
            print(f"    WCAG: {check.wcag_criterion} ({check.wcag_level}), Type: {check.check_type}")
            print()
        
        print("="*60)
        print(f"TOTAL: {len(checks)} checks")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(debug_checks())

