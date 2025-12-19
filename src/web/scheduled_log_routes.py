"""Routes for scheduled scan logs."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.database.scheduled_scan_log_repository import ScheduledScanLogRepository
from src.database.models import User
from src.web.dependencies import get_current_active_user

router = APIRouter(tags=["scheduled_scan_logs"])
templates = Jinja2Templates(directory="templates")


@router.get("/scheduled-logs", response_class=HTMLResponse)
async def scheduled_logs_page(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Render the scheduled scan logs page."""
    return templates.TemplateResponse("scheduled_logs.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "scheduled_logs"
    })


@router.get("/api/scheduled-logs")
async def get_scheduled_logs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    sort_by: str = Query("executed_at", regex="^(executed_at|status|start_url|duration_seconds)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get scheduled scan logs with filtering and sorting."""
    repo = ScheduledScanLogRepository(db)

    # Parse dates if provided
    start_datetime = None
    end_datetime = None

    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")

    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")

    # Get logs
    logs = await repo.get_user_logs(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        status=status,
        start_date=start_datetime,
        end_date=end_datetime,
        sort_by=sort_by,
        sort_order=sort_order
    )

    # Get total count for pagination
    total_count = await repo.get_log_count(
        user_id=current_user.id,
        status=status,
        start_date=start_datetime,
        end_date=end_datetime
    )

    return {
        "logs": [{
            "id": log.id,
            "scheduled_scan_id": log.scheduled_scan_id,
            "start_url": log.start_url,
            "status": log.status.value,
            "scan_id": log.scan_id,
            "pages_scanned": log.pages_scanned,
            "total_violations": log.total_violations,
            "error_message": log.error_message,
            "executed_at": log.executed_at.isoformat(),
            "duration_seconds": log.duration_seconds,
            "email_sent": log.email_sent
        } for log in logs],
        "total": total_count,
        "limit": limit,
        "offset": offset
    }


@router.get("/api/scheduled-logs/statistics")
async def get_log_statistics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get statistics about scheduled scan logs."""
    repo = ScheduledScanLogRepository(db)
    stats = await repo.get_log_statistics(current_user.id)
    return stats


@router.delete("/api/scheduled-logs/{log_id}")
async def delete_log(
    log_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a single log entry."""
    repo = ScheduledScanLogRepository(db)
    log = await repo.get_log_by_id(log_id)

    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    if log.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this log")

    await repo.delete_log(log_id)
    return {"message": "Log deleted successfully"}


@router.post("/api/scheduled-logs/bulk-delete")
async def bulk_delete_logs(
    log_ids: List[int],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete multiple log entries."""
    if not log_ids:
        raise HTTPException(status_code=400, detail="No log IDs provided")

    repo = ScheduledScanLogRepository(db)
    deleted_count = await repo.delete_logs_by_ids(log_ids, current_user.id)

    return {
        "message": f"Successfully deleted {deleted_count} log(s)",
        "deleted_count": deleted_count
    }

