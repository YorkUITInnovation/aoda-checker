"""Test API endpoint for check configurations."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.check_repository import CheckConfigRepository
from src.database import get_db_session
import json


async def test_api_data():
    """Test what data would be returned by the API."""
    print("🔍 Testing API data for frame-title check...\n", flush=True)
    
    try:
        async with get_db_session() as db:
            repo = CheckConfigRepository(db)
            
            # Get frame-title check
            check = await repo.get_check_by_id("frame-title")
            
            if not check:
                print("❌ frame-title check not found!", flush=True)
                return
            
            # Format as it would be returned by API
            api_data = {
                "id": check.id,
                "check_id": check.check_id,
                "check_name": check.check_name,
                "description": check.description,
                "enabled": check.enabled,
                "severity": check.severity.value if check.severity else None,
                "wcag_criterion": check.wcag_criterion,
                "wcag_level": check.wcag_level,
                "aoda_required": check.aoda_required,
                "wcag21_only": check.wcag21_only,
                "check_type": check.check_type,
                "help_url": check.help_url
            }
            
            print("API Response for frame-title:", flush=True)
            print(json.dumps(api_data, indent=2), flush=True)
            
            # Check for None values
            none_fields = [k for k, v in api_data.items() if v is None]
            if none_fields:
                print(f"\n⚠️  Warning: These fields are None: {', '.join(none_fields)}", flush=True)
            else:
                print("\n✅ All fields have values!", flush=True)
        
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_api_data())

