"""Routes for managing scheduled scans."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.database.scheduled_scan_repository import ScheduledScanRepository
from src.database.models import User, ScheduleFrequency
from src.web.dependencies import get_current_active_user
from src.utils.scheduler_service import scheduler_service

router = APIRouter(tags=["scheduled_scans"])
templates = Jinja2Templates(directory="templates")


class ScheduledScanCreate(BaseModel):
    """Request model for creating a scheduled scan."""
    start_url: str = Field(..., description="URL to scan")
    max_pages: int = Field(50, ge=1, description="Maximum pages to scan")
    max_depth: int = Field(3, ge=1, le=10, description="Maximum crawl depth")
    same_domain_only: bool = Field(True, description="Only scan same domain")
    frequency: str = Field(..., description="Frequency: daily, weekly, monthly, yearly")
    schedule_time: str = Field(..., description="Time in HH:MM format (24-hour)")
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="Day of week (0=Monday, 6=Sunday) for weekly")
    day_of_month: Optional[int] = Field(None, ge=1, le=31, description="Day of month for monthly/yearly")
    month_of_year: Optional[int] = Field(None, ge=1, le=12, description="Month of year for yearly")
    email_notifications: bool = Field(True, description="Enable email notifications")
    notify_on_violations: bool = Field(True, description="Notify when any violations found")
    notify_on_errors: bool = Field(True, description="Notify when errors found")

    @validator('schedule_time')
    def validate_time_format(cls, v):
        """Validate time format."""
        try:
            hour, minute = map(int, v.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
            return f"{hour:02d}:{minute:02d}"
        except:
            raise ValueError("Time must be in HH:MM format (24-hour)")

    @validator('frequency')
    def validate_frequency(cls, v):
        """Validate frequency value."""
        if v not in ['daily', 'weekly', 'monthly', 'yearly']:
            raise ValueError("Frequency must be daily, weekly, monthly, or yearly")
        return v


class ScheduledScanUpdate(BaseModel):
    """Request model for updating a scheduled scan."""
    max_pages: Optional[int] = Field(None, ge=1)
    max_depth: Optional[int] = Field(None, ge=1, le=10)
    same_domain_only: Optional[bool] = None
    frequency: Optional[str] = None
    schedule_time: Optional[str] = None
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    month_of_year: Optional[int] = Field(None, ge=1, le=12)
    email_notifications: Optional[bool] = None
    notify_on_violations: Optional[bool] = None
    notify_on_errors: Optional[bool] = None
    is_active: Optional[bool] = None


class ScheduledScanResponse(BaseModel):
    """Response model for scheduled scan."""
    id: int
    start_url: str
    max_pages: int
    max_depth: int
    same_domain_only: bool
    scan_mode: str
    frequency: str
    schedule_time: str
    day_of_week: Optional[int]
    day_of_month: Optional[int]
    month_of_year: Optional[int]
    email_notifications: bool
    notify_on_violations: bool
    notify_on_errors: bool
    is_active: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    created_at: datetime
    updated_at: datetime


@router.get("/schedule/new", response_class=HTMLResponse)
async def schedule_scan_form(
    request: Request,
    scan_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Show form to schedule a new scan."""
    from src.database.repository import ScanRepository

    # If scan_id provided, pre-fill form with that scan's data
    scan_data = None
    if scan_id:
        scan_repo = ScanRepository(db)
        scan = await scan_repo.get_scan_by_id(scan_id)
        if scan and scan.user_id == current_user.id:
            scan_data = {
                "start_url": scan.start_url,
                "max_pages": scan.max_pages,
                "max_depth": scan.max_depth,
                "same_domain_only": bool(scan.same_domain_only)
            }

    return templates.TemplateResponse("schedule_scan.html", {
        "request": request,
        "current_user": current_user,
        "scan_data": scan_data
    })


@router.post("/api/scheduled-scans")
async def create_scheduled_scan(
    scheduled_scan: ScheduledScanCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new scheduled scan."""
    repo = ScheduledScanRepository(db)

    # Create scheduled scan (without scan_mode - will use user's check configuration)
    new_scheduled_scan = await repo.create_scheduled_scan(
        user_id=current_user.id,
        start_url=scheduled_scan.start_url,
        max_pages=scheduled_scan.max_pages,
        max_depth=scheduled_scan.max_depth,
        same_domain_only=scheduled_scan.same_domain_only,
        frequency=scheduled_scan.frequency,
        schedule_time=scheduled_scan.schedule_time,
        day_of_week=scheduled_scan.day_of_week,
        day_of_month=scheduled_scan.day_of_month,
        month_of_year=scheduled_scan.month_of_year,
        email_notifications=scheduled_scan.email_notifications,
        notify_on_violations=scheduled_scan.notify_on_violations,
        notify_on_errors=scheduled_scan.notify_on_errors
    )

    # Add to scheduler
    await scheduler_service.add_scheduled_scan(new_scheduled_scan)

    return {
        "id": new_scheduled_scan.id,
        "message": "Scheduled scan created successfully",
        "next_run": new_scheduled_scan.next_run.isoformat() if new_scheduled_scan.next_run else None
    }


@router.get("/api/scheduled-scans")
async def get_scheduled_scans(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all scheduled scans for the current user."""
    repo = ScheduledScanRepository(db)
    scheduled_scans = await repo.get_user_scheduled_scans(current_user.id)

    return [{
        "id": scan.id,
        "start_url": scan.start_url,
        "max_pages": scan.max_pages,
        "max_depth": scan.max_depth,
        "same_domain_only": bool(scan.same_domain_only),
        "scan_mode": scan.scan_mode,
        "frequency": scan.frequency.value,
        "schedule_time": scan.schedule_time,
        "day_of_week": scan.day_of_week,
        "day_of_month": scan.day_of_month,
        "month_of_year": scan.month_of_year,
        "email_notifications": scan.email_notifications,
        "notify_on_violations": scan.notify_on_violations,
        "notify_on_errors": scan.notify_on_errors,
        "is_active": scan.is_active,
        "last_run": scan.last_run.isoformat() if scan.last_run else None,
        "next_run": scan.next_run.isoformat() if scan.next_run else None,
        "created_at": scan.created_at.isoformat(),
        "updated_at": scan.updated_at.isoformat()
    } for scan in scheduled_scans]


@router.get("/api/scheduled-scans/{schedule_id}")
async def get_scheduled_scan(
    schedule_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific scheduled scan."""
    repo = ScheduledScanRepository(db)
    scheduled_scan = await repo.get_scheduled_scan_by_id(schedule_id)

    if not scheduled_scan:
        raise HTTPException(status_code=404, detail="Scheduled scan not found")

    if scheduled_scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this scheduled scan")

    return {
        "id": scheduled_scan.id,
        "start_url": scheduled_scan.start_url,
        "max_pages": scheduled_scan.max_pages,
        "max_depth": scheduled_scan.max_depth,
        "same_domain_only": bool(scheduled_scan.same_domain_only),
        "scan_mode": scheduled_scan.scan_mode,
        "frequency": scheduled_scan.frequency.value,
        "schedule_time": scheduled_scan.schedule_time,
        "day_of_week": scheduled_scan.day_of_week,
        "day_of_month": scheduled_scan.day_of_month,
        "month_of_year": scheduled_scan.month_of_year,
        "email_notifications": scheduled_scan.email_notifications,
        "notify_on_violations": scheduled_scan.notify_on_violations,
        "notify_on_errors": scheduled_scan.notify_on_errors,
        "is_active": scheduled_scan.is_active,
        "last_run": scheduled_scan.last_run.isoformat() if scheduled_scan.last_run else None,
        "next_run": scheduled_scan.next_run.isoformat() if scheduled_scan.next_run else None,
        "created_at": scheduled_scan.created_at.isoformat(),
        "updated_at": scheduled_scan.updated_at.isoformat()
    }


@router.put("/api/scheduled-scans/{schedule_id}")
async def update_scheduled_scan(
    schedule_id: int,
    update_data: ScheduledScanUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a scheduled scan."""
    repo = ScheduledScanRepository(db)
    scheduled_scan = await repo.get_scheduled_scan_by_id(schedule_id)

    if not scheduled_scan:
        raise HTTPException(status_code=404, detail="Scheduled scan not found")

    if scheduled_scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this scheduled scan")

    # Update only provided fields
    update_dict = update_data.dict(exclude_unset=True)
    updated_scan = await repo.update_scheduled_scan(schedule_id, **update_dict)

    # Update in scheduler
    await scheduler_service.update_scheduled_scan(updated_scan)

    return {"message": "Scheduled scan updated successfully"}


@router.delete("/api/scheduled-scans/{schedule_id}")
async def delete_scheduled_scan(
    schedule_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a scheduled scan."""
    repo = ScheduledScanRepository(db)
    scheduled_scan = await repo.get_scheduled_scan_by_id(schedule_id)

    if not scheduled_scan:
        raise HTTPException(status_code=404, detail="Scheduled scan not found")

    if scheduled_scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this scheduled scan")

    # Remove from scheduler
    await scheduler_service.remove_scheduled_scan(schedule_id)

    # Delete from database
    await repo.delete_scheduled_scan(schedule_id)

    return {"message": "Scheduled scan deleted successfully"}


@router.post("/api/scheduled-scans/{schedule_id}/toggle")
async def toggle_scheduled_scan(
    schedule_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle active status of a scheduled scan."""
    repo = ScheduledScanRepository(db)
    scheduled_scan = await repo.get_scheduled_scan_by_id(schedule_id)

    if not scheduled_scan:
        raise HTTPException(status_code=404, detail="Scheduled scan not found")

    if scheduled_scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this scheduled scan")

    # Toggle active status
    updated_scan = await repo.toggle_active_status(schedule_id)

    # Update in scheduler
    await scheduler_service.update_scheduled_scan(updated_scan)

    return {
        "message": f"Scheduled scan {'activated' if updated_scan.is_active else 'deactivated'}",
        "is_active": updated_scan.is_active
    }

