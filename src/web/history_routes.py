"""Additional API endpoints for scan history management."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.database.repository import ScanRepository
from src.database.models import Scan

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/scans")
async def get_scan_history(
    limit: int = Query(50, ge=1, le=100),
    url: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get scan history with optional URL filter."""
    repo = ScanRepository(db)

    if url:
        scans = await repo.get_scans_by_url(url, limit)
    else:
        scans = await repo.get_recent_scans(limit)

    return [{
        "scan_id": scan.scan_id,
        "start_url": scan.start_url,
        "status": scan.status.value,
        "pages_scanned": scan.pages_scanned,
        "total_violations": scan.total_violations,
        "max_pages": scan.max_pages,
        "max_depth": scan.max_depth,
        "start_time": scan.start_time.isoformat(),
        "end_time": scan.end_time.isoformat() if scan.end_time else None
    } for scan in scans]


@router.get("/statistics")
async def get_statistics(db: AsyncSession = Depends(get_db)):
    """Get overall scan statistics."""
    repo = ScanRepository(db)
    stats = await repo.get_scan_statistics()

    # Convert enum keys to strings
    scans_by_status = {
        status.value if hasattr(status, 'value') else str(status): count
        for status, count in stats["scans_by_status"].items()
    }

    return {
        "total_scans": stats["total_scans"],
        "scans_by_status": scans_by_status,
        "total_violations": stats["total_violations"]
    }


@router.delete("/scans/{scan_id}")
async def delete_scan(scan_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a scan from history."""
    repo = ScanRepository(db)
    deleted = await repo.delete_scan(scan_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Scan not found")

    return {"message": "Scan deleted successfully"}

