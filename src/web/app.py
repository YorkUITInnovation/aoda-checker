"""FastAPI web application."""
import asyncio
import logging
from pathlib import Path
from typing import Dict
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ScanRequest, ScanResult
from src.core import AccessibilityCrawler
from src.config import settings
from src.database import init_db, get_db
from src.database.repository import ScanRepository
from src.database.models import ScanStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("Initializing database...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.warning("Application will continue without database persistence")

    yield

    # Shutdown
    logger.info("Shutting down application...")


# Create FastAPI app with lifespan
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

# Setup templates
templates = Jinja2Templates(directory="templates")

# Setup static files
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory storage for active scan results (will also persist to database)
scan_results: Dict[str, ScanResult] = {}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/scan")
async def start_scan(
    scan_request: ScanRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Start a new accessibility scan."""
    logger.info(f"Starting scan for {scan_request.url}")

    # Create crawler and start scan in background
    crawler = AccessibilityCrawler(scan_request)
    scan_id = crawler.scan_result.scan_id

    # Store initial result in memory
    scan_results[scan_id] = crawler.scan_result

    # Run scan in background
    background_tasks.add_task(run_scan, crawler, scan_id)

    return {
        "scan_id": scan_id,
        "status": "started",
        "message": "Scan started successfully"
    }


async def run_scan(crawler: AccessibilityCrawler, scan_id: str):
    """Run the scan and update results."""
    from src.database import get_db_session
    from src.database.repository import ScanRepository

    try:
        result = await crawler.crawl()
        scan_results[scan_id] = result
        logger.info(f"Scan {scan_id} completed")

        # Persist to database
        try:
            async with get_db_session() as db:
                repo = ScanRepository(db)
                await repo.create_scan(result)
                logger.info(f"Scan {scan_id} saved to database")
        except Exception as db_error:
            logger.error(f"Failed to save scan {scan_id} to database: {db_error}")
            # Continue even if database save fails

    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {str(e)}", exc_info=True)
        if scan_id in scan_results:
            scan_results[scan_id].status = "failed"
            scan_results[scan_id].end_time = datetime.now()
            scan_results[scan_id].error_message = str(e)

            # Try to update database
            try:
                async with get_db_session() as db:
                    repo = ScanRepository(db)
                    await repo.update_scan_status(scan_id, ScanStatus.FAILED, str(e))
            except Exception as db_error:
                logger.error(f"Failed to update scan status in database: {db_error}")

        logger.info(f"Scan {scan_id} completed")
    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {str(e)}", exc_info=True)
        if scan_id in scan_results:
            scan_results[scan_id].status = "failed"
            scan_results[scan_id].end_time = datetime.now()
            scan_results[scan_id].error_message = str(e)


@app.get("/api/scan/{scan_id}")
async def get_scan_status(scan_id: str):
    """Get the status of a scan."""
    if scan_id not in scan_results:
        raise HTTPException(status_code=404, detail="Scan not found")

    result = scan_results[scan_id]

    response = {
        "scan_id": scan_id,
        "status": result.status,
        "pages_scanned": result.pages_scanned,
        "pages_with_violations": result.pages_with_violations,
        "total_violations": result.total_violations,
        "violations_by_impact": result.get_violations_by_impact(),
        "start_time": result.start_time.isoformat(),
        "end_time": result.end_time.isoformat() if result.end_time else None,
        "duration": result.duration
    }

    # Include error message if scan failed
    if result.status == "failed" and result.error_message:
        response["error_message"] = result.error_message

    return response


@app.get("/api/scan/{scan_id}/results")
async def get_scan_results(scan_id: str):
    """Get detailed scan results."""
    if scan_id not in scan_results:
        raise HTTPException(status_code=404, detail="Scan not found")

    result = scan_results[scan_id]
    return result




@app.get("/results/{scan_id}", response_class=HTMLResponse)
async def results_page(request: Request, scan_id: str, db: AsyncSession = Depends(get_db)):
    """Render the results page."""
    # Try to get from memory first
    result = scan_results.get(scan_id)

    # If not in memory, try to load from database
    if not result:
        try:
            repo = ScanRepository(db)
            db_scan = await repo.get_scan(scan_id)

            if not db_scan:
                raise HTTPException(status_code=404, detail="Scan not found")

            # Convert database scan to ScanResult model
            result = db_scan.to_scan_result()
        except Exception as e:
            logger.error(f"Error loading scan from database: {e}")
            raise HTTPException(status_code=404, detail="Scan not found")

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "scan_result": result,
            "violations_by_impact": result.get_violations_by_impact()
        }
    )


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """Render the scan history page."""
    return templates.TemplateResponse("history.html", {"request": request})


# Include history routes
from src.web.history_routes import router as history_router
app.include_router(history_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)

