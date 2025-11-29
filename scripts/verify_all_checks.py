"""Verify and fix all checks in the database."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.check_repository import CheckConfigRepository, get_default_check_configurations
from src.database import get_db_session


async def verify_and_fix_all_checks():
    """Verify all checks have complete data and fix any issues."""
    print("🔍 Verifying all check configurations...\n", flush=True)
    
    try:
        async with get_db_session() as db:
            repo = CheckConfigRepository(db)
            
            # Get all existing checks
            all_checks = await repo.get_all_checks()
            print(f"Found {len(all_checks)} checks in database\n", flush=True)
            
            # Get default configurations
            defaults = get_default_check_configurations()
            default_dict = {check['check_id']: check for check in defaults}
            
            issues_found = 0
            fixes_applied = 0
            
            # Check each existing check
            for check in all_checks:
                has_issue = False
                issues = []
                
                # Check for missing or incomplete data
                if not check.description or check.description.strip() == '':
                    issues.append("missing description")
                    has_issue = True
                
                if not check.severity:
                    issues.append("missing severity")
                    has_issue = True
                    
                if not check.wcag_criterion:
                    issues.append("missing WCAG criterion")
                    has_issue = True
                    
                if not check.wcag_level:
                    issues.append("missing WCAG level")
                    has_issue = True
                    
                if not check.check_type or check.check_type.strip() == '':
                    issues.append("missing check type")
                    has_issue = True
                
                if has_issue:
                    issues_found += 1
                    print(f"❌ {check.check_id}: {check.check_name}", flush=True)
                    print(f"   Issues: {', '.join(issues)}", flush=True)
                    
                    # Try to fix from defaults
                    if check.check_id in default_dict:
                        default = default_dict[check.check_id]
                        print(f"   Applying fix from defaults...", flush=True)
                        
                        check.description = default['description']
                        check.severity = default['severity']
                        check.wcag_criterion = default['wcag_criterion']
                        check.wcag_level = default['wcag_level']
                        check.check_type = default['check_type']
                        check.help_url = default['help_url']
                        check.tags = default['tags']
                        check.aoda_required = default['aoda_required']
                        check.wcag21_only = default['wcag21_only']
                        
                        fixes_applied += 1
                        print(f"   ✅ Fixed\n", flush=True)
                    else:
                        print(f"   ⚠️  No default found for this check\n", flush=True)
                else:
                    print(f"✅ {check.check_id}: OK", flush=True)
            
            if fixes_applied > 0:
                await db.commit()
                print(f"\n💾 Committed {fixes_applied} fixes to database", flush=True)
            
            print(f"\n" + "="*60, flush=True)
            print(f"Summary:", flush=True)
            print(f"  Total checks: {len(all_checks)}", flush=True)
            print(f"  Issues found: {issues_found}", flush=True)
            print(f"  Fixes applied: {fixes_applied}", flush=True)
            print(f"  Checks OK: {len(all_checks) - issues_found}", flush=True)
            print("="*60, flush=True)
            
            if issues_found == 0:
                print("\n🎉 All checks are properly configured!", flush=True)
            elif fixes_applied == issues_found:
                print("\n🎉 All issues fixed successfully!", flush=True)
            else:
                print(f"\n⚠️  {issues_found - fixes_applied} checks still have issues", flush=True)
        
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(verify_and_fix_all_checks())

