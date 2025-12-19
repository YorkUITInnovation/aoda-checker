"""Repository for scheduled scan log operations."""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import ScheduledScanLog, ScheduledScanLogStatus


class ScheduledScanLogRepository:
    """Repository for managing scheduled scan log records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_log(
        self,
        scheduled_scan_id: int,
        user_id: int,
        start_url: str,
        status: ScheduledScanLogStatus,
        scan_id: Optional[str] = None,
        pages_scanned: int = 0,
        total_violations: int = 0,
        error_message: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        email_sent: bool = False
    ) -> ScheduledScanLog:
        """Create a new scheduled scan log entry."""
        log = ScheduledScanLog(
            scheduled_scan_id=scheduled_scan_id,
            user_id=user_id,
            start_url=start_url,
            status=status,
            scan_id=scan_id,
            pages_scanned=pages_scanned,
            total_violations=total_violations,
            error_message=error_message,
            duration_seconds=duration_seconds,
            email_sent=email_sent,
            executed_at=datetime.utcnow()
        )

        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def get_log_by_id(self, log_id: int) -> Optional[ScheduledScanLog]:
        """Get a log entry by ID."""
        result = await self.session.execute(
            select(ScheduledScanLog)
            .options(selectinload(ScheduledScanLog.scheduled_scan))
            .where(ScheduledScanLog.id == log_id)
        )
        return result.scalar_one_or_none()

    async def get_user_logs(
        self,
        user_id: int,
        limit: int = 1000,
        offset: int = 0,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sort_by: str = "executed_at",
        sort_order: str = "desc"
    ) -> List[ScheduledScanLog]:
        """Get all logs for a user with optional filtering and sorting."""
        query = select(ScheduledScanLog).where(ScheduledScanLog.user_id == user_id)

        # Apply filters
        if status:
            query = query.where(ScheduledScanLog.status == status)

        if start_date:
            query = query.where(ScheduledScanLog.executed_at >= start_date)

        if end_date:
            query = query.where(ScheduledScanLog.executed_at <= end_date)

        # Apply sorting
        sort_column = getattr(ScheduledScanLog, sort_by, ScheduledScanLog.executed_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_logs_for_scheduled_scan(
        self,
        scheduled_scan_id: int,
        limit: int = 100
    ) -> List[ScheduledScanLog]:
        """Get all logs for a specific scheduled scan."""
        result = await self.session.execute(
            select(ScheduledScanLog)
            .where(ScheduledScanLog.scheduled_scan_id == scheduled_scan_id)
            .order_by(desc(ScheduledScanLog.executed_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_log_count(
        self,
        user_id: int,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """Get count of logs for a user with optional filtering."""
        from sqlalchemy import func

        query = select(func.count(ScheduledScanLog.id)).where(ScheduledScanLog.user_id == user_id)

        if status:
            query = query.where(ScheduledScanLog.status == status)

        if start_date:
            query = query.where(ScheduledScanLog.executed_at >= start_date)

        if end_date:
            query = query.where(ScheduledScanLog.executed_at <= end_date)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def delete_log(self, log_id: int) -> bool:
        """Delete a log entry."""
        log = await self.get_log_by_id(log_id)
        if not log:
            return False

        await self.session.delete(log)
        await self.session.commit()
        return True

    async def delete_logs_by_ids(self, log_ids: List[int], user_id: int) -> int:
        """Delete multiple log entries by IDs (only if they belong to the user)."""
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(ScheduledScanLog)
            .where(
                and_(
                    ScheduledScanLog.id.in_(log_ids),
                    ScheduledScanLog.user_id == user_id
                )
            )
        )
        await self.session.commit()
        return result.rowcount

    async def delete_old_logs(self, days: int = 90) -> int:
        """Delete logs older than specified days."""
        from sqlalchemy import delete
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await self.session.execute(
            delete(ScheduledScanLog).where(ScheduledScanLog.executed_at < cutoff_date)
        )
        await self.session.commit()
        return result.rowcount

    async def get_log_statistics(self, user_id: int) -> dict:
        """Get statistics about scheduled scan logs for a user."""
        from sqlalchemy import func

        # Total logs
        total_result = await self.session.execute(
            select(func.count(ScheduledScanLog.id))
            .where(ScheduledScanLog.user_id == user_id)
        )
        total = total_result.scalar_one()

        # Success count
        success_result = await self.session.execute(
            select(func.count(ScheduledScanLog.id))
            .where(
                and_(
                    ScheduledScanLog.user_id == user_id,
                    ScheduledScanLog.status == ScheduledScanLogStatus.SUCCESS
                )
            )
        )
        success = success_result.scalar_one()

        # Failed count
        failed_result = await self.session.execute(
            select(func.count(ScheduledScanLog.id))
            .where(
                and_(
                    ScheduledScanLog.user_id == user_id,
                    ScheduledScanLog.status == ScheduledScanLogStatus.FAILED
                )
            )
        )
        failed = failed_result.scalar_one()

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": round((success / total * 100) if total > 0 else 0, 1)
        }

