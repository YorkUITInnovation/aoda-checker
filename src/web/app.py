"""FastAPI web application."""
import asyncio
import logging
from pathlib import Path
from typing import Dict
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware
from pydantic import HttpUrl

from src.models import ScanRequest, ScanResult, ScanMode
from src.core import AccessibilityCrawler
from src.config import settings
from src.database import init_db, get_db
from src.database.repository import ScanRepository
from src.database.models import ScanStatus, User
from src.web.dependencies import get_current_user, get_current_active_user

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

# Add session middleware for cookie-based authentication
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="aoda_session",
    max_age=settings.jwt_expiration_minutes * 60,  # Convert minutes to seconds
    same_site="lax",
    https_only=False  # Set to True in production with HTTPS
)

# Setup templates
templates = Jinja2Templates(directory="templates")

# Setup static files
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# Custom exception handler for 401 Unauthorized
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions, redirecting to login for 401 on HTML pages."""
    if exc.status_code == 401:
        # Check if this is an API request or a page request
        is_api_request = (
            request.url.path.startswith('/api/') or
            'application/json' in request.headers.get('accept', '').lower() or
            'application/json' in request.headers.get('content-type', '').lower()
        )

        if not is_api_request:
            # For HTML page requests, redirect to login
            next_url = str(request.url.path)
            if request.url.query:
                next_url += f"?{request.url.query}"
            return RedirectResponse(
                url=f"/login?next={next_url}",
                status_code=303
            )

    # For API requests or other status codes, return JSON error
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# In-memory storage for active scan results (will also persist to database)
scan_results: Dict[str, ScanResult] = {}

# Register batch scan routes
from src.web.batch_scan_routes import router as batch_router
app.include_router(batch_router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, current_user: User = Depends(get_current_active_user)):
    """Render the main page."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "home"
    })


@app.post("/api/scan")
async def start_scan(
    scan_request: ScanRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a new accessibility scan."""
    logger.info(f"Starting scan for {scan_request.url} by user {current_user.username}")

    # Create crawler with user_id for checkpointing
    crawler = AccessibilityCrawler(scan_request, user_id=current_user.id)
    scan_id = crawler.scan_result.scan_id

    # Store initial result in memory
    scan_results[scan_id] = crawler.scan_result

    # Run scan in background
    background_tasks.add_task(run_scan, crawler, scan_id, current_user.id)

    return {
        "scan_id": scan_id,
        "status": "started",
        "message": "Scan started successfully"
    }


@app.post("/api/scan/resume/{scan_id}")
async def resume_scan(
    scan_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Resume an interrupted scan from last checkpoint."""
    logger.info(f"Resuming scan {scan_id} by user {current_user.username}")

    try:
        # Get the original scan from database
        repo = ScanRepository(db)
        original_scan = await repo.get_scan_by_id(scan_id)

        if not original_scan:
            raise HTTPException(status_code=404, detail="Scan not found")

        # Check permissions
        if not current_user.is_admin and original_scan.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Check if scan is already completed
        if original_scan.status == ScanStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail="Scan is already completed and cannot be resumed"
            )

        # Create scan request from original scan configuration
        scan_request = ScanRequest(
            url=HttpUrl(original_scan.start_url),
            max_pages=original_scan.max_pages,
            max_depth=original_scan.max_depth,
            same_domain_only=bool(original_scan.same_domain_only),
            restrict_to_path=True,  # Preserve original behavior
            enable_screenshots=False,  # Default
            scan_mode=ScanMode(original_scan.scan_mode)
        )

        # Create crawler with resume capability
        crawler = AccessibilityCrawler(
            scan_request,
            user_id=current_user.id,
            resume_scan_id=scan_id  # Enable resume mode
        )

        # Use the same scan_id for continuity
        crawler.scan_result.scan_id = scan_id

        # Store result in memory
        scan_results[scan_id] = crawler.scan_result

        # Run resumed scan in background
        background_tasks.add_task(run_scan, crawler, scan_id, current_user.id)

        return {
            "scan_id": scan_id,
            "status": "resumed",
            "message": "Scan resumed from last checkpoint"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume scan {scan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to resume scan: {str(e)}")


async def run_scan(crawler: AccessibilityCrawler, scan_id: str, user_id: int):
    """Run the scan and update results."""
    from src.database import get_db_session
    from src.database.repository import ScanRepository
    from src.database.models import ScanStatus

    try:
        result = await crawler.crawl()
        scan_results[scan_id] = result
        logger.info(f"Scan {scan_id} completed")

        # Update database with final status
        # Note: Scan record already exists from initial checkpoint
        try:
            async with get_db_session() as db:
                repo = ScanRepository(db)

                # Check if scan already exists (it should, from initial checkpoint)
                existing_scan = await repo.get_scan_by_id(scan_id)

                if existing_scan:
                    # Update existing scan with final status
                    await repo.update_scan_status(
                        scan_id=scan_id,
                        status=ScanStatus.COMPLETED,
                        error_message=None
                    )
                    logger.info(f"Scan {scan_id} status updated to COMPLETED in database")
                else:
                    # Fallback: create scan if it doesn't exist (shouldn't happen with checkpointing)
                    await repo.create_scan(result, user_id)
                    logger.info(f"Scan {scan_id} created in database (no initial checkpoint)")

        except Exception as db_error:
            logger.error(f"Failed to update scan {scan_id} in database: {db_error}")
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




@app.get("/api/scan/{scan_id}")
async def get_scan_status(scan_id: str, db: AsyncSession = Depends(get_db)):
    """Get the status of a scan."""
    result = None

    # First try memory
    if scan_id in scan_results:
        result = scan_results[scan_id]
    else:
        # Try database
        try:
            repo = ScanRepository(db)
            db_scan = await repo.get_scan_by_id(scan_id)
            if db_scan:
                result = await repo.convert_to_scan_result(db_scan)
        except Exception as e:
            logger.error(f"Error loading scan from database: {e}")

    if not result:
        raise HTTPException(status_code=404, detail="Scan not found")

    response = {
        "scan_id": scan_id,
        "status": result.status,
        "start_url": result.start_url,
        "max_pages": result.max_pages,
        "max_depth": result.max_depth,
        "pages_scanned": result.pages_scanned,
        "pages_with_violations": result.pages_with_violations,
        "total_violations": result.total_violations,
        "violations_by_impact": result.get_violations_by_impact(),  # Deprecated
        "violations_by_severity": result.get_violations_by_severity(),  # New
        "start_time": result.start_time.isoformat(),
        "end_time": result.end_time.isoformat() if result.end_time else None,
        "duration": result.duration,
        "estimated_time_remaining": result.estimated_time_remaining,
        "estimated_time_remaining_formatted": result.estimated_time_remaining_formatted
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


@app.get("/api/scan/{scan_id}/download/docx")
async def download_docx_report(
    scan_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Download scan results as a DOCX report."""
    from fastapi.responses import StreamingResponse
    from src.utils.docx_report import generate_docx_report

    # Try to get from memory first
    result = scan_results.get(scan_id)

    # If not in memory, try database
    if not result:
        try:
            repo = ScanRepository(db)
            db_scan = await repo.get_scan_by_id(scan_id)

            if not db_scan:
                raise HTTPException(status_code=404, detail="Scan not found")

            # Check permissions
            if not current_user.is_admin and db_scan.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied")

            result = await repo.convert_to_scan_result(db_scan)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error loading scan for DOCX download: {e}")
            raise HTTPException(status_code=404, detail="Scan not found")

    # Generate DOCX report
    try:
        docx_file = generate_docx_report(result)

        # Create filename
        from urllib.parse import urlparse
        domain = urlparse(result.start_url).netloc or 'scan'
        safe_domain = domain.replace('.', '_').replace(':', '_')
        timestamp = result.start_time.strftime('%Y%m%d_%H%M%S')
        filename = f"accessibility_report_{safe_domain}_{timestamp}.docx"

        return StreamingResponse(
            docx_file,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        logger.error(f"Error generating DOCX report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate report")


@app.get("/api/scan/{scan_id}/download/xlsx")
async def download_xlsx_report(
    scan_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Download scan results as an Excel (XLSX) report."""
    from fastapi.responses import StreamingResponse
    from src.utils.excel_report import generate_excel_report

    # Try to get from memory first
    result = scan_results.get(scan_id)

    # If not in memory, try database
    if not result:
        try:
            repo = ScanRepository(db)
            db_scan = await repo.get_scan_by_id(scan_id)

            if not db_scan:
                raise HTTPException(status_code=404, detail="Scan not found")

            # Check permissions
            if not current_user.is_admin and db_scan.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied")

            result = await repo.convert_to_scan_result(db_scan)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error loading scan for XLSX download: {e}")
            raise HTTPException(status_code=404, detail="Scan not found")

    # Generate Excel report
    try:
        excel_file = generate_excel_report(result)

        # Create filename
        from urllib.parse import urlparse
        domain = urlparse(result.start_url).netloc or 'scan'
        safe_domain = domain.replace('.', '_').replace(':', '_')
        timestamp = result.start_time.strftime('%Y%m%d_%H%M%S')
        filename = f"accessibility_report_{safe_domain}_{timestamp}.xlsx"

        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        logger.error(f"Error generating Excel report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate Excel report")


@app.get("/api/discover-urls")
async def discover_urls_endpoint(
    url: str,
    max_depth: int = 2,
    max_pages: int = 100,
    same_domain_only: bool = True,
    restrict_to_path: bool = True,
    current_user: User = Depends(get_current_active_user)
):
    """
    Discover all URLs on a website without scanning.

    Query Parameters:
        url: Starting URL to discover from
        max_depth: Maximum depth to crawl (1-10, default 2)
        max_pages: Maximum pages to discover (1-10000, default 100)
        same_domain_only: Only discover URLs on same domain (default true)
        restrict_to_path: Only discover URLs within starting path (default true)
    """
    from src.utils.url_discovery import discover_urls

    # Validate max_depth
    if max_depth < 1 or max_depth > 10:
        raise HTTPException(status_code=400, detail="max_depth must be between 1 and 10")

    # Validate max_pages
    if max_pages < 1 or max_pages > 10000:
        raise HTTPException(status_code=400, detail="max_pages must be between 1 and 10000")

    # Validate URL
    try:
        from pydantic import HttpUrl
        HttpUrl(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL format")

    logger.info(f"URL discovery requested by {current_user.username} for {url} (max_depth={max_depth}, max_pages={max_pages})")

    try:
        result = await discover_urls(
            url=url,
            max_depth=max_depth,
            max_pages=max_pages,
            same_domain_only=same_domain_only,
            restrict_to_path=restrict_to_path
        )
        return result
    except Exception as e:
        logger.error(f"URL discovery failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"URL discovery failed: {str(e)}")


@app.get("/discover", response_class=HTMLResponse)
async def discover_page(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Render the URL discovery page."""
    return templates.TemplateResponse("discover.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "discover"
    })


@app.get("/results/{scan_id}", response_class=HTMLResponse)
async def results_page(
    request: Request,
    scan_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
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

            # Check if user has permission to view this scan
            if not current_user.is_admin and db_scan.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Access denied")

            # Convert database scan to ScanResult model
            result = db_scan.to_scan_result()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error loading scan from database: {e}")
            raise HTTPException(status_code=404, detail="Scan not found")

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "current_user": current_user,
            "scan_result": result,
            "violations_by_impact": result.get_violations_by_impact(),  # Keep for backward compatibility
            "violations_by_severity": result.get_violations_by_severity()  # New severity-based counts
        }
    )


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Render the scan history page."""
    return templates.TemplateResponse("history.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "history"
    })


# Include authentication routes
from src.web.auth_routes import router as auth_router
app.include_router(auth_router)

# Include admin routes
from src.web.admin_routes import router as admin_router
app.include_router(admin_router)

# Include check configuration routes
from src.web.check_config_routes import router as check_config_router, user_router as user_check_router
app.include_router(check_config_router)
app.include_router(user_check_router)

# Include history routes
from src.web.history_routes import router as history_router
app.include_router(history_router)


@app.get("/checks", response_class=HTMLResponse)
async def user_checks_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Render the user check configuration page."""
    return templates.TemplateResponse("user_checks.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "user-checks"
    })


@app.get("/help", response_class=HTMLResponse)
async def help_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Render the main help/documentation page."""
    return templates.TemplateResponse("help.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "help"
    })


@app.get("/help/scans", response_class=HTMLResponse)
async def help_scans_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Render the accessibility scans help page."""
    return templates.TemplateResponse("help_scans.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "help"
    })


@app.get("/help/discover", response_class=HTMLResponse)
async def help_discover_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Render the discover URLs help page."""
    return templates.TemplateResponse("help_discover.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "help"
    })


@app.get("/help/results", response_class=HTMLResponse)
async def help_results_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Render the results help page."""
    return templates.TemplateResponse("help_results.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "help"
    })


@app.get("/help/history", response_class=HTMLResponse)
async def help_history_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Render the history help page."""
    return templates.TemplateResponse("help_history.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "help"
    })


@app.get("/help/checks", response_class=HTMLResponse)
async def help_checks_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Render the check configuration help page."""
    return templates.TemplateResponse("help_checks.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "help"
    })


@app.get("/help/faq", response_class=HTMLResponse)
async def help_faq_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Render the FAQ help page."""
    return templates.TemplateResponse("help_faq.html", {
        "request": request,
        "current_user": current_user,
        "active_page": "help"
    })


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
