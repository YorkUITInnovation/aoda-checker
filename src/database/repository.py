"""Repository for scan database operations."""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import Scan, PageScan, Violation, ScanStatus
from src.models import ScanResult, PageResult, AccessibilityViolation


class ScanRepository:
    """Repository for managing scan records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_scan(self, scan_result: ScanResult, user_id: int) -> Scan:
        """Create a new scan record."""
        scan = Scan(
            scan_id=scan_result.scan_id,
            start_url=scan_result.start_url,
            status=ScanStatus(scan_result.status),
            user_id=user_id,
            max_pages=scan_result.max_pages,
            max_depth=scan_result.max_depth,
            same_domain_only=1 if scan_result.same_domain_only else 0,
            pages_scanned=scan_result.pages_scanned,
            pages_with_violations=scan_result.pages_with_violations,
            total_violations=scan_result.total_violations,
            start_time=scan_result.start_time,
            end_time=scan_result.end_time,
            error_message=scan_result.error_message
        )

        self.session.add(scan)
        await self.session.flush()

        # Add page scans
        for page_result in scan_result.page_results:
            await self._create_page_scan(scan.id, page_result)

        await self.session.commit()
        return scan

    async def _create_page_scan(self, scan_db_id: int, page_result: PageResult) -> PageScan:
        """Create a page scan record."""
        page_scan = PageScan(
            scan_id=scan_db_id,
            url=page_result.url,
            title=page_result.title,
            status_code=page_result.status_code,
            violation_count=page_result.violation_count,
            passes=page_result.passes,
            incomplete=page_result.incomplete,
            inapplicable=page_result.inapplicable,
            error=page_result.error,
            scanned_at=datetime.utcnow()
        )

        self.session.add(page_scan)
        await self.session.flush()

        # Add violations
        for violation in page_result.violations:
            await self._create_violation(page_scan.id, violation)

        return page_scan

    async def _create_violation(self, page_db_id: int, violation: AccessibilityViolation) -> Violation:
        """Create a violation record."""
        violation_record = Violation(
            page_id=page_db_id,
            violation_id=violation.id,
            impact=violation.impact.value,
            description=violation.description,
            help=violation.help,
            help_url=violation.help_url,
            tags=violation.tags,
            nodes=violation.nodes,
            found_at=datetime.utcnow()
        )

        self.session.add(violation_record)
        return violation_record

    async def get_scan_by_id(self, scan_id: str) -> Optional[Scan]:
        """Get a scan by its scan_id."""
        result = await self.session.execute(
            select(Scan)
            .options(selectinload(Scan.pages).selectinload(PageScan.violations))
            .where(Scan.scan_id == scan_id)
        )
        return result.scalar_one_or_none()

    async def get_scan(self, scan_id: str) -> Optional[Scan]:
        """Alias for get_scan_by_id for consistency."""
        return await self.get_scan_by_id(scan_id)

    async def get_recent_scans(self, limit: int = 50, user_id: Optional[int] = None) -> List[Scan]:
        """Get recent scans ordered by start time, optionally filtered by user."""
        query = select(Scan).order_by(desc(Scan.start_time)).limit(limit)

        if user_id is not None:
            query = query.where(Scan.user_id == user_id)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_scans_by_url(self, url: str, limit: int = 10, user_id: Optional[int] = None) -> List[Scan]:
        """Get scans for a specific URL, optionally filtered by user."""
        query = (
            select(Scan)
            .where(Scan.start_url == url)
            .order_by(desc(Scan.start_time))
            .limit(limit)
        )

        if user_id is not None:
            query = query.where(Scan.user_id == user_id)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_scans_by_user(self, user_id: int, limit: int = 50) -> List[Scan]:
        """Get all scans for a specific user."""
        result = await self.session.execute(
            select(Scan)
            .where(Scan.user_id == user_id)
            .order_by(desc(Scan.start_time))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_scans(self, limit: int = 50) -> List[Scan]:
        """Get all scans (admin only)."""
        result = await self.session.execute(
            select(Scan)
            .order_by(desc(Scan.start_time))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_scan_status(self, scan_id: str, status: ScanStatus, error_message: Optional[str] = None):
        """Update scan status."""
        result = await self.session.execute(
            select(Scan).where(Scan.scan_id == scan_id)
        )
        scan = result.scalar_one_or_none()

        if scan:
            scan.status = status
            if status in [ScanStatus.COMPLETED, ScanStatus.FAILED]:
                scan.end_time = datetime.utcnow()
            if error_message:
                scan.error_message = error_message
            await self.session.commit()

    async def delete_scan(self, scan_id: str) -> bool:
        """Delete a scan and all its related data."""
        result = await self.session.execute(
            select(Scan).where(Scan.scan_id == scan_id)
        )
        scan = result.scalar_one_or_none()

        if scan:
            await self.session.delete(scan)
            await self.session.commit()
            return True
        return False

    async def get_scan_statistics(self) -> dict:
        """Get overall statistics."""
        # Total scans
        total_result = await self.session.execute(
            select(func.count(Scan.id))
        )
        total_scans = total_result.scalar()

        # Scans by status
        status_result = await self.session.execute(
            select(Scan.status, func.count(Scan.id))
            .group_by(Scan.status)
        )
        scans_by_status = dict(status_result.all())

        # Total violations
        violations_result = await self.session.execute(
            select(func.sum(Scan.total_violations))
        )
        total_violations = violations_result.scalar() or 0

        return {
            "total_scans": total_scans,
            "scans_by_status": scans_by_status,
            "total_violations": total_violations
        }

    async def convert_to_scan_result(self, scan: Scan) -> ScanResult:
        """Convert database Scan to ScanResult model."""
        # Load pages and violations if not already loaded
        await self.session.refresh(scan, ['pages'])

        page_results = []
        for page in scan.pages:
            await self.session.refresh(page, ['violations'])

            violations = [
                AccessibilityViolation(
                    id=v.violation_id,
                    impact=v.impact,
                    description=v.description,
                    help=v.help,
                    help_url=v.help_url,
                    tags=v.tags,
                    nodes=v.nodes
                )
                for v in page.violations
            ]

            page_result = PageResult(
                url=page.url,
                title=page.title,
                status_code=page.status_code,
                violations=violations,
                passes=page.passes,
                incomplete=page.incomplete,
                inapplicable=page.inapplicable,
                error=page.error
            )
            page_results.append(page_result)

        scan_result = ScanResult(
            scan_id=scan.scan_id,
            start_url=scan.start_url,
            start_time=scan.start_time,
            end_time=scan.end_time,
            status=scan.status.value,
            pages_scanned=scan.pages_scanned,
            pages_with_violations=scan.pages_with_violations,
            total_violations=scan.total_violations,
            page_results=page_results,
            error_message=scan.error_message
        )

        return scan_result

