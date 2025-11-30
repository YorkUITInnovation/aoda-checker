"""Additional API endpoints for scan history management."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.database.repository import ScanRepository
from src.database.user_repository import UserRepository
from src.database.models import Scan, User
from src.web.dependencies import get_current_active_user, get_current_admin_user

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/scans")
async def get_scan_history(
    limit: int = Query(50, ge=1, le=100),
    url: Optional[str] = None,
    user_id: Optional[int] = None,
    all_scans: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get scan history with optional filters.

    - Regular users: Only see their own scans
    - Admins: Can see their own scans (default), all scans (all_scans=true), or filter by user_id
    """
    repo = ScanRepository(db)

    # Determine which scans to retrieve
    if current_user.is_admin:
        if all_scans:
            # Admin viewing all scans
            if url:
                scans = await repo.get_scans_by_url(url, limit, user_id=None)
            else:
                scans = await repo.get_all_scans(limit)
        elif user_id:
            # Admin viewing specific user's scans
            if url:
                scans = await repo.get_scans_by_url(url, limit, user_id=user_id)
            else:
                scans = await repo.get_scans_by_user(user_id, limit)
        else:
            # Admin viewing their own scans
            if url:
                scans = await repo.get_scans_by_url(url, limit, user_id=current_user.id)
            else:
                scans = await repo.get_scans_by_user(current_user.id, limit)
    else:
        # Regular user can only see their own scans
        if url:
            scans = await repo.get_scans_by_url(url, limit, user_id=current_user.id)
        else:
            scans = await repo.get_scans_by_user(current_user.id, limit)

    return [{
        "scan_id": scan.scan_id,
        "start_url": scan.start_url,
        "status": scan.status.value,
        "pages_scanned": scan.pages_scanned,
        "total_violations": scan.total_violations,
        "max_pages": scan.max_pages,
        "max_depth": scan.max_depth,
        "scan_mode": getattr(scan, 'scan_mode', 'aoda'),
        "start_time": scan.start_time.isoformat(),
        "end_time": scan.end_time.isoformat() if scan.end_time else None,
        "user_id": scan.user_id
    } for scan in scans]


@router.get("/users")
async def get_users_for_filter(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of users for admin filtering (admin only)."""
    user_repo = UserRepository(db)
    users = await user_repo.get_all_users()

    return [{
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name
    } for user in users]


@router.get("/statistics")
async def get_statistics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get scan statistics.

    - Regular users: See only their own statistics
    - Admins: See site-wide statistics
    """
    repo = ScanRepository(db)

    # Non-admin users only see their own statistics
    user_id = None if current_user.is_admin else current_user.id
    stats = await repo.get_scan_statistics(user_id=user_id)

    # Convert enum keys to strings
    scans_by_status = {
        status.value if hasattr(status, 'value') else str(status): count
        for status, count in stats["scans_by_status"].items()
    }

    return {
        "total_scans": stats["total_scans"],
        "scans_by_status": scans_by_status,
        "total_violations": stats["total_violations"],
        "is_user_specific": not current_user.is_admin  # Indicator for frontend
    }


@router.delete("/scans/{scan_id}")
async def delete_scan(
    scan_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a scan from history."""
    repo = ScanRepository(db)

    # Get the scan to check ownership
    scan = await repo.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Check if user has permission to delete
    if not current_user.is_admin and scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    deleted = await repo.delete_scan(scan_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Scan not found")

    return {"message": "Scan deleted successfully"}

