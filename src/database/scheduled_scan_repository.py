"""Repository for scheduled scan database operations."""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ScheduledScan, User


class ScheduledScanRepository:
    """Repository for managing scheduled scan records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_scheduled_scan(
        self,
        user_id: int,
        start_url: str,
        frequency: str,
        schedule_time: str,
        max_pages: int = 50,
        max_depth: int = 3,
        same_domain_only: bool = True,
        email_notifications: bool = True,
        notify_on_violations: bool = True,
        notify_on_errors: bool = True,
        day_of_week: Optional[int] = None,
        day_of_month: Optional[int] = None,
        month_of_year: Optional[int] = None
    ) -> ScheduledScan:
        """Create a new scheduled scan (will use user's check configuration)."""
        scheduled_scan = ScheduledScan(
            user_id=user_id,
            start_url=start_url,
            max_pages=max_pages,
            max_depth=max_depth,
            same_domain_only=1 if same_domain_only else 0,
            frequency=frequency,
            schedule_time=schedule_time,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            month_of_year=month_of_year,
            email_notifications=email_notifications,
            notify_on_violations=notify_on_violations,
            notify_on_errors=notify_on_errors,
            is_active=True
        )

        self.session.add(scheduled_scan)
        await self.session.commit()
        await self.session.refresh(scheduled_scan)
        return scheduled_scan

    async def get_scheduled_scan_by_id(self, schedule_id: int) -> Optional[ScheduledScan]:
        """Get a scheduled scan by ID."""
        result = await self.session.execute(
            select(ScheduledScan).where(ScheduledScan.id == schedule_id)
        )
        return result.scalar_one_or_none()

    async def get_user_scheduled_scans(self, user_id: int) -> List[ScheduledScan]:
        """Get all scheduled scans for a user."""
        result = await self.session.execute(
            select(ScheduledScan)
            .where(ScheduledScan.user_id == user_id)
            .order_by(ScheduledScan.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_scheduled_scans(self) -> List[ScheduledScan]:
        """Get all active scheduled scans."""
        result = await self.session.execute(
            select(ScheduledScan).where(ScheduledScan.is_active == True)
        )
        return list(result.scalars().all())

    async def update_scheduled_scan(
        self,
        schedule_id: int,
        **kwargs
    ) -> Optional[ScheduledScan]:
        """Update a scheduled scan."""
        scheduled_scan = await self.get_scheduled_scan_by_id(schedule_id)
        if not scheduled_scan:
            return None

        for key, value in kwargs.items():
            if hasattr(scheduled_scan, key):
                if key == 'same_domain_only' and isinstance(value, bool):
                    setattr(scheduled_scan, key, 1 if value else 0)
                else:
                    setattr(scheduled_scan, key, value)

        scheduled_scan.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(scheduled_scan)
        return scheduled_scan

    async def update_last_run(self, schedule_id: int, last_run: datetime):
        """Update the last run time of a scheduled scan."""
        scheduled_scan = await self.get_scheduled_scan_by_id(schedule_id)
        if scheduled_scan:
            scheduled_scan.last_run = last_run
            await self.session.commit()

    async def update_next_run(self, schedule_id: int, next_run: datetime):
        """Update the next run time of a scheduled scan."""
        scheduled_scan = await self.get_scheduled_scan_by_id(schedule_id)
        if scheduled_scan:
            scheduled_scan.next_run = next_run
            await self.session.commit()

    async def delete_scheduled_scan(self, schedule_id: int) -> bool:
        """Delete a scheduled scan."""
        scheduled_scan = await self.get_scheduled_scan_by_id(schedule_id)
        if not scheduled_scan:
            return False

        await self.session.delete(scheduled_scan)
        await self.session.commit()
        return True

    async def toggle_active_status(self, schedule_id: int) -> Optional[ScheduledScan]:
        """Toggle the active status of a scheduled scan."""
        scheduled_scan = await self.get_scheduled_scan_by_id(schedule_id)
        if not scheduled_scan:
            return None

        scheduled_scan.is_active = not scheduled_scan.is_active
        scheduled_scan.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(scheduled_scan)
        return scheduled_scan

