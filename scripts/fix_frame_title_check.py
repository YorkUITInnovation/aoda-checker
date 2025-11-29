"""Update existing frame-title check with complete information."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.database.session import engine
from src.database.check_repository import CheckConfigRepository, CheckSeverity
from src.database import get_db_session


async def fix_frame_title_check():
    """Update or create the frame-title check with complete data."""
    print("🔧 Fixing frame-title check configuration...", flush=True)
    
    try:
        async with get_db_session() as db:
            repo = CheckConfigRepository(db)
            
            # Check if frame-title exists
            existing = await repo.get_check_by_id("frame-title")
            
            if existing:
                print(f"   Found existing check: {existing.check_name}", flush=True)
                print(f"   Current values:", flush=True)
                print(f"     - Description: {existing.description}", flush=True)
                print(f"     - Severity: {existing.severity.value if existing.severity else 'None'}", flush=True)
                print(f"     - WCAG: {existing.wcag_criterion} ({existing.wcag_level})", flush=True)
                print(f"     - Type: {existing.check_type}", flush=True)
                
                # Update with complete data
                print("   Updating with complete data...", flush=True)
                existing.description = "Ensures <iframe> and <frame> elements have an accessible name"
                existing.severity = CheckSeverity.ERROR
                existing.wcag_criterion = "4.1.2"
                existing.wcag_level = "A"
                existing.aoda_required = True
                existing.wcag21_only = False
                existing.check_type = "axe"
                existing.help_url = "https://dequeuniversity.com/rules/axe/4.4/frame-title"
                existing.tags = ["cat.text-alternatives", "wcag2a", "wcag412", "section508"]
                
                await db.commit()
                print("   ✅ Updated frame-title check successfully", flush=True)
            else:
                print("   Check does not exist, creating it...", flush=True)
                await repo.create_check(
                    check_id="frame-title",
                    check_name="Frames must have an accessible name",
                    description="Ensures <iframe> and <frame> elements have an accessible name",
                    enabled=True,
                    severity=CheckSeverity.ERROR,
                    wcag_criterion="4.1.2",
                    wcag_level="A",
                    aoda_required=True,
                    wcag21_only=False,
                    check_type="axe",
                    help_url="https://dequeuniversity.com/rules/axe/4.4/frame-title",
                    tags=["cat.text-alternatives", "wcag2a", "wcag412", "section508"]
                )
                print("   ✅ Created frame-title check successfully", flush=True)
            
            # Verify the fix
            print("\n   Verifying...", flush=True)
            updated = await repo.get_check_by_id("frame-title")
            if updated:
                print(f"   ✅ Check verified:", flush=True)
                print(f"     - Name: {updated.check_name}", flush=True)
                print(f"     - Description: {updated.description}", flush=True)
                print(f"     - Severity: {updated.severity.value}", flush=True)
                print(f"     - WCAG: {updated.wcag_criterion} ({updated.wcag_level})", flush=True)
                print(f"     - Type: {updated.check_type}", flush=True)
                print(f"     - Help URL: {updated.help_url}", flush=True)
            
        print("\n🎉 Fix completed successfully!", flush=True)
        
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(fix_frame_title_check())

