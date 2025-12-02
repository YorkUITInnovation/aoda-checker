"""Batch scanning routes for multiple URL scans."""
import asyncio
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.database.models import User
from src.web.dependencies import get_current_active_user
from src.models import ScanRequest, ScanMode
from src.core import AccessibilityCrawler

router = APIRouter(prefix="/api/batch", tags=["batch"])

# Global state for batch scans (in production, use Redis or database)
batch_scan_status = {}
batch_scan_lock = asyncio.Lock()


class BatchScanRequest(BaseModel):
    """Batch scan request model."""
    urls: List[str]
    max_pages: int = 25
    max_depth: int = 3
    same_domain_only: bool = True
    scan_mode: str = "aoda"


class BatchScanStatus(BaseModel):
    """Batch scan status model."""
    batch_id: str
    total_urls: int
    completed: int
    failed: int
    in_progress: int
    status: str  # 'running', 'completed', 'cancelled', 'failed'
    current_url: Optional[str] = None
    scan_ids: List[str] = []
    failed_urls: List[str] = []
    start_time: datetime
    end_time: Optional[datetime] = None


async def run_batch_scans(
    batch_id: str,
    urls: List[str],
    max_pages: int,
    max_depth: int,
    same_domain_only: bool,
    scan_mode: str,
    user_id: int
):
    """Run batch scans with concurrency control."""
    from src.database.repository import ScanRepository
    from src.database.session import get_db_session
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Starting batch scan {batch_id} for {len(urls)} URLs")

    max_concurrent = 3  # Maximum concurrent scans
    semaphore = asyncio.Semaphore(max_concurrent)

    async def scan_single_url(url: str, index: int):
        """Scan a single URL with semaphore control."""
        async with semaphore:
            # Check if batch was cancelled
            async with batch_scan_lock:
                if batch_scan_status[batch_id]["status"] == "cancelled":
                    logger.info(f"Batch {batch_id} cancelled, skipping {url}")
                    return None

            # Update current URL
            async with batch_scan_lock:
                batch_scan_status[batch_id]["current_url"] = url
                batch_scan_status[batch_id]["in_progress"] += 1

            logger.info(f"Batch {batch_id}: Starting scan {index + 1}/{len(urls)} - {url}")

            try:
                # Create scan request
                scan_request = ScanRequest(
                    url=url,
                    max_pages=max_pages,
                    max_depth=max_depth,
                    same_domain_only=same_domain_only,
                    scan_mode=ScanMode(scan_mode)
                )

                # Run the scan WITHOUT user_id to prevent automatic DB saving
                # We'll save manually after scan completes
                logger.info(f"Batch {batch_id}: Crawling {url}")
                crawler = AccessibilityCrawler(scan_request, user_id=None)
                result = await crawler.crawl()

                # Save to database using a new session
                logger.info(f"Batch {batch_id}: Saving results for {url} (scan_id: {result.scan_id})")
                async with get_db_session() as db_session:
                    scan_repo = ScanRepository(db_session)
                    await scan_repo.create_scan(result, user_id)

                # Update status
                async with batch_scan_lock:
                    batch_scan_status[batch_id]["completed"] += 1
                    batch_scan_status[batch_id]["in_progress"] -= 1
                    batch_scan_status[batch_id]["scan_ids"].append(result.scan_id)

                logger.info(f"Batch {batch_id}: Successfully completed {url}")
                return result.scan_id

            except Exception as e:
                logger.error(f"Batch {batch_id}: Error scanning {url}: {str(e)}")
                logger.exception(e)

                # Update failed status
                async with batch_scan_lock:
                    batch_scan_status[batch_id]["failed"] += 1
                    batch_scan_status[batch_id]["in_progress"] -= 1
                    batch_scan_status[batch_id]["failed_urls"].append(url)

                return None

    # Run all scans
    logger.info(f"Batch {batch_id}: Starting {len(urls)} scans with max {max_concurrent} concurrent")
    tasks = [scan_single_url(url, i) for i, url in enumerate(urls)]
    await asyncio.gather(*tasks, return_exceptions=True)

    # Mark batch as completed
    async with batch_scan_lock:
        if batch_scan_status[batch_id]["status"] != "cancelled":
            batch_scan_status[batch_id]["status"] = "completed"
        batch_scan_status[batch_id]["end_time"] = datetime.utcnow()
        batch_scan_status[batch_id]["current_url"] = None

        logger.info(f"Batch {batch_id} finished: {batch_scan_status[batch_id]['completed']} completed, "
                   f"{batch_scan_status[batch_id]['failed']} failed")


@router.post("/scan", response_model=dict)
async def start_batch_scan(
    request: BatchScanRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a batch scan of multiple URLs."""
    if not request.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")

    if len(request.urls) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 URLs allowed per batch")

    # Generate batch ID
    batch_id = str(uuid.uuid4())

    # Initialize batch status
    async with batch_scan_lock:
        batch_scan_status[batch_id] = {
            "batch_id": batch_id,
            "total_urls": len(request.urls),
            "completed": 0,
            "failed": 0,
            "in_progress": 0,
            "status": "running",
            "current_url": None,
            "scan_ids": [],
            "failed_urls": [],
            "start_time": datetime.utcnow(),
            "end_time": None,
            "user_id": current_user.id
        }

    # Start batch scan in background
    background_tasks.add_task(
        run_batch_scans,
        batch_id,
        request.urls,
        request.max_pages,
        request.max_depth,
        request.same_domain_only,
        request.scan_mode,
        current_user.id
    )

    return {
        "batch_id": batch_id,
        "message": f"Batch scan started for {len(request.urls)} URLs",
        "total_urls": len(request.urls)
    }


@router.get("/status/{batch_id}")
async def get_batch_status(
    batch_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get the status of a batch scan."""
    async with batch_scan_lock:
        if batch_id not in batch_scan_status:
            raise HTTPException(status_code=404, detail="Batch scan not found")

        status = batch_scan_status[batch_id].copy()

        # Check ownership
        if status["user_id"] != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")

        # Remove user_id from response
        status.pop("user_id", None)

        # Convert datetime to ISO format
        if isinstance(status.get("start_time"), datetime):
            status["start_time"] = status["start_time"].isoformat()
        if isinstance(status.get("end_time"), datetime):
            status["end_time"] = status["end_time"].isoformat()

        return status


@router.post("/cancel/{batch_id}")
async def cancel_batch_scan(
    batch_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Cancel a running batch scan."""
    async with batch_scan_lock:
        if batch_id not in batch_scan_status:
            raise HTTPException(status_code=404, detail="Batch scan not found")

        status = batch_scan_status[batch_id]

        # Check ownership
        if status["user_id"] != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Access denied")

        if status["status"] != "running":
            raise HTTPException(status_code=400, detail="Batch scan is not running")

        # Mark as cancelled
        batch_scan_status[batch_id]["status"] = "cancelled"
        batch_scan_status[batch_id]["end_time"] = datetime.utcnow()

    return {"message": "Batch scan cancelled successfully"}


@router.get("/active")
async def get_active_batch_scans(
    current_user: User = Depends(get_current_active_user)
):
    """Get all active batch scans for the current user."""
    async with batch_scan_lock:
        active_batches = []
        for batch_id, status in batch_scan_status.items():
            if status["user_id"] == current_user.id and status["status"] == "running":
                status_copy = status.copy()
                status_copy.pop("user_id", None)

                # Convert datetime to ISO format
                if isinstance(status_copy.get("start_time"), datetime):
                    status_copy["start_time"] = status_copy["start_time"].isoformat()
                if isinstance(status_copy.get("end_time"), datetime):
                    status_copy["end_time"] = status_copy["end_time"].isoformat()

                active_batches.append(status_copy)

        return active_batches

