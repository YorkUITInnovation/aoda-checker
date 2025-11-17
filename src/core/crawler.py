"""Core crawler functionality."""
import asyncio
import logging
from urllib.parse import urljoin, urlparse
from typing import Set, List, Optional
from datetime import datetime
import uuid

from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup
from axe_playwright_python.async_playwright import Axe

from src.models import (
    PageResult,
    ScanResult,
    AccessibilityViolation,
    ViolationImpact,
    ScanRequest
)
from src.config import settings

logger = logging.getLogger(__name__)


class AccessibilityCrawler:
    """Crawler that tests web pages for accessibility compliance."""

    def __init__(self, scan_request: ScanRequest):
        """Initialize the crawler with scan parameters."""
        self.start_url = str(scan_request.url)
        self.max_pages = scan_request.max_pages
        self.max_depth = scan_request.max_depth
        self.same_domain_only = scan_request.same_domain_only
        self.restrict_to_path = scan_request.restrict_to_path
        self.enable_screenshots = scan_request.enable_screenshots

        self.visited_urls: Set[str] = set()

        # Normalize the start URL to ensure consistency
        normalized_start = AccessibilityCrawler._normalize_url(self.start_url) or self.start_url
        self.to_visit: List[tuple[str, int]] = [(normalized_start, 0)]  # (url, depth)
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

    async def crawl(self) -> ScanResult:
        """Crawl the website and test for accessibility."""
        logger.info(f"Starting crawl of {self.start_url}")
        logger.info(f"Configuration: max_pages={self.max_pages}, max_depth={self.max_depth}, same_domain_only={self.same_domain_only}, restrict_to_path={self.restrict_to_path}")
        logger.info(f"Performance: request_delay={settings.request_delay}s, timeout={settings.timeout}ms, screenshots={'enabled' if self.enable_screenshots else 'disabled'}")
        logger.info(f"Domain: {self.domain}")
        if self.restrict_to_path:
            logger.info(f"Path restriction: {self.start_path or '/'}")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)

                while self.to_visit and len(self.visited_urls) < self.max_pages:
                    current_url, depth = self.to_visit.pop(0)

                    if current_url in self.visited_urls:
                        continue

                    if depth > self.max_depth:
                        continue

                    self.visited_urls.add(current_url)

                    # Scan the page
                    page_result, page_content = await self._scan_page(browser, current_url)
                    self.scan_result.page_results.append(page_result)
                    self.scan_result.pages_scanned += 1

                    if page_result.has_violations:
                        self.scan_result.pages_with_violations += 1

                    self.scan_result.total_violations += page_result.violation_count

                    # Extract links if not at max depth (use page content)
                    if depth < self.max_depth and not page_result.error and page_content:
                        links = self._extract_links_from_html(current_url, page_content)
                        logger.info(f"Found {len(links)} links on {current_url} at depth {depth}")
                        new_links = 0
                        for link in links:
                            if link not in self.visited_urls and link not in [url for url, _ in self.to_visit]:
                                self.to_visit.append((link, depth + 1))
                                new_links += 1
                        logger.info(f"Added {new_links} new links to queue. Queue size: {len(self.to_visit)}")

                    # Throttling
                    await asyncio.sleep(settings.request_delay)

                await browser.close()

            self.scan_result.end_time = datetime.now()
            self.scan_result.status = "completed"
            logger.info(f"Crawl completed. Scanned {self.scan_result.pages_scanned} pages")

        except Exception as e:
            logger.error(f"Crawl failed: {str(e)}", exc_info=True)
            self.scan_result.status = "failed"
            self.scan_result.end_time = datetime.now()
            self.scan_result.error_message = f"{type(e).__name__}: {str(e)}"
            # Re-raise so the caller can handle it
            raise

        return self.scan_result

    async def _scan_page(self, browser: Browser, url: str) -> tuple[PageResult, Optional[str]]:
        """Scan a single page for accessibility issues."""
        logger.info(f"Scanning: {url}")

        page_result = PageResult(url=url)
        page = None
        page_content = None

        try:
            page = await browser.new_page()
            response = await page.goto(url, timeout=settings.timeout, wait_until="domcontentloaded")

            if response:
                page_result.status_code = response.status

            # Get page title
            page_result.title = await page.title()

            # Get page content for link extraction
            page_content = await page.content()

            # Run axe accessibility tests
            axe = Axe()
            axe_results = await axe.run(page)

            # Convert AxeResults object to dictionary
            if hasattr(axe_results, 'response'):
                results = axe_results.response
            elif hasattr(axe_results, 'to_dict'):
                results = axe_results.to_dict()
            elif isinstance(axe_results, dict):
                results = axe_results
            else:
                # Try to access as object attributes
                results = {
                    'violations': getattr(axe_results, 'violations', []),
                    'passes': getattr(axe_results, 'passes', []),
                    'incomplete': getattr(axe_results, 'incomplete', []),
                    'inapplicable': getattr(axe_results, 'inapplicable', [])
                }

            # Process violations and capture screenshots
            violations_list = results.get("violations", [])
            screenshot_count = 0  # Track screenshots per page

            for violation in violations_list:
                nodes_with_screenshots = []

                # Process each node and try to capture a screenshot
                for node in violation.get("nodes", []):
                    node_data = dict(node)  # Copy the node data

                    # Only capture screenshot if enabled and under limit
                    if (self.enable_screenshots and
                        screenshot_count < settings.max_screenshots_per_page and
                        node.get("target")):
                        try:
                            selector = node["target"][0] if isinstance(node["target"], list) else node["target"]
                            element = await page.query_selector(selector)

                            if element:
                                # Capture screenshot as base64
                                screenshot_bytes = await element.screenshot()
                                import base64
                                screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                                node_data['screenshot'] = f"data:image/png;base64,{screenshot_base64}"
                                screenshot_count += 1
                                logger.debug(f"Captured screenshot {screenshot_count}/{settings.max_screenshots_per_page} for element: {selector}")
                        except Exception as screenshot_error:
                            logger.debug(f"Could not capture screenshot for {node.get('target')}: {screenshot_error}")

                    nodes_with_screenshots.append(node_data)

                page_result.violations.append(
                    AccessibilityViolation(
                        id=violation["id"],
                        impact=ViolationImpact(violation.get("impact", "minor")),
                        description=violation["description"],
                        help=violation["help"],
                        help_url=violation["helpUrl"],
                        tags=violation["tags"],
                        nodes=nodes_with_screenshots
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
                await page.close()

        return page_result, page_content

    async def _extract_links(self, browser: Browser, url: str) -> List[str]:
        """Extract all links from a page."""
        links = []
        page = None

        try:
            page = await browser.new_page()
            await page.goto(url, timeout=settings.timeout, wait_until="domcontentloaded")

            # Get all links
            link_elements = await page.query_selector_all("a[href]")

            for element in link_elements:
                href = await element.get_attribute("href")
                if href:
                    absolute_url = urljoin(url, href)
                    normalized_url = self._normalize_url(absolute_url)

                    if normalized_url and self._should_crawl(normalized_url):
                        links.append(normalized_url)

        except Exception as e:
            logger.error(f"Error extracting links from {url}: {str(e)}")

        finally:
            if page:
                await page.close()

        return links

    def _extract_links_from_html(self, base_url: str, html_content: str) -> List[str]:
        """Extract links from HTML content using BeautifulSoup."""
        links = []

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            link_elements = soup.find_all('a', href=True)

            logger.info(f"BeautifulSoup found {len(link_elements)} anchor tags")

            for element in link_elements:
                href = element['href']
                if href:
                    absolute_url = urljoin(base_url, href)
                    normalized_url = self._normalize_url(absolute_url)

                    if normalized_url and self._should_crawl(normalized_url):
                        # Avoid duplicates in this batch
                        if normalized_url not in links:
                            links.append(normalized_url)

            logger.info(f"After filtering, {len(links)} valid links remain")

        except Exception as e:
            logger.error(f"Error extracting links from HTML: {str(e)}")

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

            # Check scheme
            if parsed.scheme not in ["http", "https"]:
                return False

            # Check domain if same_domain_only
            # Normalize domain comparison (ignore www prefix and http/https difference)
            if self.same_domain_only:
                url_domain = parsed.netloc.lower().replace('www.', '')
                target_domain = self.domain.lower().replace('www.', '')
                if url_domain != target_domain:
                    logger.debug(f"Skipping {url} - different domain ({url_domain} != {target_domain})")
                    return False

            # Check path restriction if enabled
            if self.restrict_to_path and self.start_path:
                url_path = parsed.path.rstrip('/')
                # URL must start with the same path as the starting URL
                if not url_path.startswith(self.start_path):
                    logger.debug(f"Skipping {url} - outside path restriction (path: {url_path}, required: {self.start_path})")
                    return False

            # Skip common non-HTML resources
            skip_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg',
                             '.css', '.js', '.zip', '.doc', '.docx', '.xls', '.xlsx',
                             '.mp4', '.mp3', '.avi', '.mov', '.wmv', '.xml', '.json',
                             '.ico', '.woff', '.woff2', '.ttf', '.eot']
            if any(parsed.path.lower().endswith(ext) for ext in skip_extensions):
                logger.debug(f"Skipping {url} - file extension")
                return False

            # Skip common patterns
            skip_patterns = ['mailto:', 'tel:', 'javascript:', '#', 'data:']
            if any(url.lower().startswith(pattern) for pattern in skip_patterns):
                logger.debug(f"Skipping {url} - skip pattern")
                return False

            return True

        except:
            return False

