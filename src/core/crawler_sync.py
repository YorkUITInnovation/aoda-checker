"""Core crawler functionality - SYNCHRONOUS VERSION."""
import logging
from urllib.parse import urljoin, urlparse
from typing import Set, List, Optional
from datetime import datetime
import uuid
import time

from playwright.sync_api import sync_playwright, Page, Browser
from bs4 import BeautifulSoup

# Import axe synchronously
try:
    from axe_core_python.sync_playwright import Axe
    AXE_AVAILABLE = True
except ImportError:
    AXE_AVAILABLE = False
    logging.warning("Axe not available, using basic checks only")

from src.models import (
    PageResult,
    ScanResult,
    AccessibilityViolation,
    ViolationImpact,
    ScanRequest
)
from src.config import settings

logger = logging.getLogger(__name__)


class SyncAccessibilityCrawler:
    """Synchronous crawler that tests web pages for accessibility compliance."""

    def __init__(self, scan_request: ScanRequest):
        """Initialize the crawler with scan parameters."""
        self.start_url = str(scan_request.url)
        self.max_pages = scan_request.max_pages
        self.max_depth = scan_request.max_depth
        self.same_domain_only = scan_request.same_domain_only
        self.restrict_to_path = scan_request.restrict_to_path

        self.visited_urls: Set[str] = set()
        self.to_visit: List[tuple[str, int]] = [(self.start_url, 0)]
        self.domain = urlparse(self.start_url).netloc

        # Store the starting path for path restriction
        parsed_start = urlparse(self.start_url)
        self.start_path = parsed_start.path.rstrip('/') if parsed_start.path else ''

        self.scan_result = ScanResult(
            scan_id=str(uuid.uuid4()),
            start_url=self.start_url,
            start_time=datetime.now(),
            max_pages=self.max_pages,
            max_depth=self.max_depth,
            same_domain_only=self.same_domain_only,
            restrict_to_path=self.restrict_to_path
        )

    def crawl(self) -> ScanResult:
        """Crawl the website and test for accessibility - SYNCHRONOUS."""
        logger.info(f"Starting SYNC crawl of {self.start_url}")
        logger.info(f"Configuration: max_pages={self.max_pages}, max_depth={self.max_depth}, same_domain_only={self.same_domain_only}, restrict_to_path={self.restrict_to_path}")
        logger.info(f"Domain: {self.domain}")
        if self.restrict_to_path:
            logger.info(f"Path restriction: {self.start_path or '/'}")

        try:
            with sync_playwright() as p:
                # Use Firefox for better macOS compatibility
                browser = p.firefox.launch(headless=True)
                logger.info("Firefox browser launched")

                while self.to_visit and len(self.visited_urls) < self.max_pages:
                    current_url, depth = self.to_visit.pop(0)

                    if current_url in self.visited_urls:
                        continue

                    if depth > self.max_depth:
                        continue

                    self.visited_urls.add(current_url)

                    # Scan the page
                    page_result = self._scan_page(browser, current_url)
                    self.scan_result.page_results.append(page_result)
                    self.scan_result.pages_scanned += 1

                    if page_result.has_violations:
                        self.scan_result.pages_with_violations += 1

                    self.scan_result.total_violations += page_result.violation_count

                    # Extract links if not at max depth
                    if depth < self.max_depth and not page_result.error:
                        links = self._extract_links(browser, current_url)
                        for link in links:
                            if link not in self.visited_urls:
                                self.to_visit.append((link, depth + 1))

                    # Throttling
                    time.sleep(settings.request_delay)

                browser.close()

            self.scan_result.end_time = datetime.now()
            self.scan_result.status = "completed"
            logger.info(f"Crawl completed. Scanned {self.scan_result.pages_scanned} pages")

        except Exception as e:
            logger.error(f"Crawl failed: {str(e)}", exc_info=True)
            self.scan_result.status = "failed"
            self.scan_result.end_time = datetime.now()
            self.scan_result.error_message = f"{type(e).__name__}: {str(e)}"
            raise

        return self.scan_result

    def _scan_page(self, browser: Browser, url: str) -> PageResult:
        """Scan a single page for accessibility issues - SYNCHRONOUS."""
        logger.info(f"Scanning: {url}")

        page_result = PageResult(url=url)
        page = None

        try:
            page = browser.new_page()
            response = page.goto(url, timeout=settings.timeout, wait_until="domcontentloaded")

            if response:
                page_result.status_code = response.status

            # Get page title
            page_result.title = page.title()

            # Run axe accessibility tests if available
            if AXE_AVAILABLE:
                axe = Axe()
                results = axe.run(page)

                # Process violations
                for violation in results.get("violations", []):
                    page_result.violations.append(
                        AccessibilityViolation(
                            id=violation["id"],
                            impact=ViolationImpact(violation.get("impact", "minor")),
                            description=violation["description"],
                            help=violation["help"],
                            help_url=violation["helpUrl"],
                            tags=violation["tags"],
                            nodes=violation.get("nodes", [])
                        )
                    )

                # Store test statistics
                page_result.passes = len(results.get("passes", []))
                page_result.incomplete = len(results.get("incomplete", []))
                page_result.inapplicable = len(results.get("inapplicable", []))

        except Exception as e:
            logger.error(f"Error scanning {url}: {str(e)}")
            page_result.error = str(e)

        finally:
            if page:
                page.close()

        return page_result

    def _extract_links(self, browser: Browser, url: str) -> List[str]:
        """Extract all links from a page - SYNCHRONOUS."""
        links = []
        page = None

        try:
            page = browser.new_page()
            page.goto(url, timeout=settings.timeout, wait_until="domcontentloaded")

            # Get all links
            link_elements = page.query_selector_all("a[href]")

            for element in link_elements:
                href = element.get_attribute("href")
                if href:
                    absolute_url = urljoin(url, href)
                    normalized_url = self._normalize_url(absolute_url)

                    if normalized_url and self._should_crawl(normalized_url):
                        links.append(normalized_url)

        except Exception as e:
            logger.error(f"Error extracting links from {url}: {str(e)}")

        finally:
            if page:
                page.close()

        return links

    @staticmethod
    def _normalize_url(url: str) -> Optional[str]:
        """Normalize URL by removing fragments, query params, and standardizing format."""
        try:
            parsed = urlparse(url)

            # Normalize scheme to https (prefer https over http for same domain)
            scheme = 'https' if parsed.scheme in ['http', 'https'] else parsed.scheme

            # Normalize netloc (remove www prefix for consistency)
            netloc = parsed.netloc.lower()
            if netloc.startswith('www.'):
                netloc = netloc[4:]

            # Normalize path (remove trailing slash except for root)
            path = parsed.path
            if path and path != '/':
                path = path.rstrip('/')
            elif not path:
                path = '/'

            # Build normalized URL (scheme + netloc + path, no query/fragment)
            normalized = f"{scheme}://{netloc}{path}"

            return normalized
        except:
            return None

    def _should_crawl(self, url: str) -> bool:
        """Determine if a URL should be crawled."""
        try:
            parsed = urlparse(url)

            if parsed.scheme not in ["http", "https"]:
                return False

            if self.same_domain_only and parsed.netloc != self.domain:
                return False

            # Check path restriction if enabled
            if self.restrict_to_path and self.start_path:
                url_path = parsed.path.rstrip('/')
                # URL must start with the same path as the starting URL
                if not url_path.startswith(self.start_path):
                    logger.debug(f"Skipping {url} - outside path restriction (path: {url_path}, required: {self.start_path})")
                    return False

            skip_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg',
                             '.css', '.js', '.zip', '.doc', '.docx', '.xls', '.xlsx']
            if any(parsed.path.lower().endswith(ext) for ext in skip_extensions):
                return False

            return True

        except:
            return False

