"""Scheduler service for running scheduled scans."""
import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.models import ScheduledScan, User
from src.database.scheduled_scan_repository import ScheduledScanRepository
from src.database.repository import ScanRepository
from src.database.user_repository import UserRepository
from src.database import get_db_session
from src.models import ScanRequest, ScanMode
from src.core import AccessibilityCrawler
from src.utils.email_service import EmailService

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing scheduled scans."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._initialized = False

    async def initialize(self):
        """Initialize the scheduler and load all active scheduled scans."""
        if self._initialized:
            return

        logger.info("Initializing scheduler service...")
        self.scheduler.start()

        # Load all active scheduled scans
        await self.reload_scheduled_scans()

        self._initialized = True
        logger.info("Scheduler service initialized successfully")

    async def reload_scheduled_scans(self):
        """Reload all active scheduled scans from the database."""
        try:
            async with get_db_session() as db:
                repo = ScheduledScanRepository(db)
                scheduled_scans = await repo.get_active_scheduled_scans()

                # Remove all existing jobs
                self.scheduler.remove_all_jobs()

                # Add jobs for each active scheduled scan
                for scheduled_scan in scheduled_scans:
                    await self._add_scheduled_scan_job(scheduled_scan)

                logger.info(f"Loaded {len(scheduled_scans)} active scheduled scans")
        except Exception as e:
            logger.error(f"Failed to reload scheduled scans: {e}")

    async def _add_scheduled_scan_job(self, scheduled_scan: ScheduledScan):
        """Add a scheduled scan job to the scheduler."""
        try:
            job_id = f"scheduled_scan_{scheduled_scan.id}"

            # Parse schedule time (HH:MM format)
            hour, minute = map(int, scheduled_scan.schedule_time.split(':'))

            # Import timezone support
            import pytz
            # Use configured timezone or default to UTC
            tz = pytz.timezone(settings.timezone if hasattr(settings, 'timezone') else 'America/Toronto')

            # Create cron trigger based on frequency with timezone
            if scheduled_scan.frequency.value == "daily":
                trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
            elif scheduled_scan.frequency.value == "weekly":
                day_of_week = scheduled_scan.day_of_week or 0
                trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute, timezone=tz)
            elif scheduled_scan.frequency.value == "monthly":
                day = scheduled_scan.day_of_month or 1
                trigger = CronTrigger(day=day, hour=hour, minute=minute, timezone=tz)
            elif scheduled_scan.frequency.value == "yearly":
                month = scheduled_scan.month_of_year or 1
                day = scheduled_scan.day_of_month or 1
                trigger = CronTrigger(month=month, day=day, hour=hour, minute=minute, timezone=tz)
            else:
                logger.error(f"Unknown frequency: {scheduled_scan.frequency}")
                return

            # Add job to scheduler
            self.scheduler.add_job(
                self._run_scheduled_scan,
                trigger=trigger,
                id=job_id,
                args=[scheduled_scan.id],
                replace_existing=True
            )

            # Update next run time
            next_run = self.scheduler.get_job(job_id).next_run_time
            async with get_db_session() as db:
                repo = ScheduledScanRepository(db)
                await repo.update_next_run(scheduled_scan.id, next_run)

            logger.info(f"Added scheduled scan job: {job_id}, next run: {next_run} ({tz})")
        except Exception as e:
            logger.error(f"Failed to add scheduled scan job for {scheduled_scan.id}: {e}", exc_info=True)

    async def _run_scheduled_scan(self, schedule_id: int):
        """Execute a scheduled scan."""
        logger.info(f"Running scheduled scan {schedule_id}...")

        start_time = datetime.utcnow()
        scan_result = None
        error_message = None
        email_sent = False

        try:
            # Get scheduled scan details first
            async with get_db_session() as db:
                scheduled_repo = ScheduledScanRepository(db)
                scheduled_scan = await scheduled_repo.get_scheduled_scan_by_id(schedule_id)

                if not scheduled_scan or not scheduled_scan.is_active:
                    logger.warning(f"Scheduled scan {schedule_id} not found or inactive")
                    return

                # Get user
                user_repo = UserRepository(db)
                user = await user_repo.get_user_by_id(scheduled_scan.user_id)

                if not user:
                    logger.error(f"User {scheduled_scan.user_id} not found for scheduled scan {schedule_id}")
                    return

                # Update last run time
                await scheduled_repo.update_last_run(schedule_id, datetime.utcnow())

                # Store user info for email (outside db context)
                user_email = user.email
                user_username = user.username
                user_first_name = user.first_name
                user_id = user.id
                start_url = scheduled_scan.start_url

            # Create scan request (outside db context)
            # Note: scan_mode not specified - crawler will use user's check configuration
            scan_request = ScanRequest(
                url=scheduled_scan.start_url,
                max_pages=scheduled_scan.max_pages,
                max_depth=scheduled_scan.max_depth,
                same_domain_only=bool(scheduled_scan.same_domain_only),
                restrict_to_path=True
            )

            # Run the scan (without user_id to prevent duplicate DB save in crawler)
            # The crawler will save to DB during __init__ if user_id is provided,
            # but we want to save only once after completion
            logger.info(f"Starting scan for {scheduled_scan.start_url} (schedule {schedule_id}) using user check configuration")
            crawler = AccessibilityCrawler(scan_request, user_id=None)
            scan_result = await crawler.crawl()

            logger.info(f"Scan completed: {scan_result.scan_id} with {scan_result.total_violations} violations")

            # Save to database (new session) - this is the only save
            async with get_db_session() as db:
                scan_repo = ScanRepository(db)
                await scan_repo.create_scan(scan_result, user_id)

            logger.info(f"Scheduled scan {schedule_id} completed and saved: {scan_result.scan_id}")

            # Send email notification if enabled and violations found
            if scheduled_scan.email_notifications and user_email:
                should_send = False
                error_count = 0
                warning_count = 0

                # Count violations by impact
                for page in scan_result.page_results:
                    for violation in page.violations:
                        if violation.impact.value in ['critical', 'serious']:
                            error_count += 1
                        else:
                            warning_count += 1

                # Determine if we should send notification
                if scheduled_scan.notify_on_errors and error_count > 0:
                    should_send = True
                elif scheduled_scan.notify_on_violations and scan_result.total_violations > 0:
                    should_send = True

                if should_send:
                    logger.info(f"Sending email notification to {user_email}")
                    # Recreate user object for email (without db session)
                    from src.database.models import User
                    temp_user = User(username=user_username, email=user_email, first_name=user_first_name, id=user_id)

                    email_sent = await EmailService.send_scan_violation_notification(
                        user=temp_user,
                        scan_id=scan_result.scan_id,
                        start_url=scan_result.start_url,
                        total_violations=scan_result.total_violations,
                        error_count=error_count,
                        warning_count=warning_count,
                        pages_scanned=scan_result.pages_scanned
                    )

                    if email_sent:
                        logger.info(f"Email notification sent successfully to {user_email}")
                    else:
                        logger.warning(f"Failed to send email notification to {user_email}")
                else:
                    logger.info(f"No email notification needed (no violations or notifications disabled)")

            # Create success log entry
            duration = int((datetime.utcnow() - start_time).total_seconds())
            async with get_db_session() as db:
                from src.database.scheduled_scan_log_repository import ScheduledScanLogRepository
                from src.database.models import ScheduledScanLogStatus

                log_repo = ScheduledScanLogRepository(db)
                await log_repo.create_log(
                    scheduled_scan_id=schedule_id,
                    user_id=user_id,
                    start_url=start_url,
                    status=ScheduledScanLogStatus.SUCCESS,
                    scan_id=scan_result.scan_id,
                    pages_scanned=scan_result.pages_scanned,
                    total_violations=scan_result.total_violations,
                    duration_seconds=duration,
                    email_sent=email_sent
                )

            logger.info(f"Scheduled scan log created for schedule {schedule_id}")

        except Exception as e:
            error_message = str(e)
            logger.error(f"Failed to run scheduled scan {schedule_id}: {e}", exc_info=True)

            # Create failure log entry
            try:
                duration = int((datetime.utcnow() - start_time).total_seconds())
                async with get_db_session() as db:
                    from src.database.scheduled_scan_log_repository import ScheduledScanLogRepository
                    from src.database.models import ScheduledScanLogStatus

                    log_repo = ScheduledScanLogRepository(db)
                    await log_repo.create_log(
                        scheduled_scan_id=schedule_id,
                        user_id=user_id if 'user_id' in locals() else 0,
                        start_url=start_url if 'start_url' in locals() else "Unknown",
                        status=ScheduledScanLogStatus.FAILED,
                        error_message=error_message,
                        duration_seconds=duration
                    )

                logger.info(f"Scheduled scan failure log created for schedule {schedule_id}")
            except Exception as log_error:
                logger.error(f"Failed to create failure log: {log_error}")

    async def add_scheduled_scan(self, scheduled_scan: ScheduledScan):
        """Add a new scheduled scan to the scheduler."""
        if scheduled_scan.is_active:
            await self._add_scheduled_scan_job(scheduled_scan)

    async def remove_scheduled_scan(self, schedule_id: int):
        """Remove a scheduled scan from the scheduler."""
        job_id = f"scheduled_scan_{schedule_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed scheduled scan job: {job_id}")

    async def update_scheduled_scan(self, scheduled_scan: ScheduledScan):
        """Update an existing scheduled scan in the scheduler."""
        await self.remove_scheduled_scan(scheduled_scan.id)
        if scheduled_scan.is_active:
            await self._add_scheduled_scan_job(scheduled_scan)

    async def shutdown(self):
        """Shutdown the scheduler."""
        if self._initialized:
            self.scheduler.shutdown()
            self._initialized = False
            logger.info("Scheduler service shut down")


# Global scheduler instance
scheduler_service = SchedulerService()

