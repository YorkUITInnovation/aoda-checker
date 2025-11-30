"""URL discovery utility for finding all URLs on a website without scanning."""
import asyncio
import logging
from typing import Set, List, Tuple, Dict
from urllib.parse import urljoin, urlparse
from datetime import datetime

from playwright.async_api import async_playwright, Browser
from bs4 import BeautifulSoup

from src.config import settings

logger = logging.getLogger(__name__)


class URLDiscoverer:
    """Discover URLs on a website without performing accessibility scans."""

    def __init__(
        self,
        start_url: str,
        max_depth: int = 2,
        max_pages: int = 100,
        same_domain_only: bool = True,
        restrict_to_path: bool = True
    ):
        """
        Initialize URL discoverer.
        
        Args:
            start_url: Starting URL to discover from
            max_depth: Maximum depth to crawl (1-10)
            max_pages: Maximum number of pages to discover (1-10000)
            same_domain_only: Only discover URLs on same domain
            restrict_to_path: Only discover URLs within starting path
        """
        self.start_url = start_url
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.same_domain_only = same_domain_only
        self.restrict_to_path = restrict_to_path

        parsed_start = urlparse(start_url)
        self.domain = parsed_start.netloc
        # Normalize domain by removing www. for comparison
        self.domain_normalized = self.domain.replace('www.', '') if self.domain.startswith('www.') else self.domain
        self.start_path = parsed_start.path.rstrip('/') if parsed_start.path else ''
        
        self.discovered_urls: Set[str] = set()
        self.to_visit: List[Tuple[str, int]] = [(start_url, 0)]
        self.visited_urls: Set[str] = set()

    async def discover(self) -> Dict:
        """
        Discover URLs by crawling.
        
        Returns:
            Dictionary containing discovered URLs and metadata
        """
        start_time = datetime.now()
        
        logger.info(f"Starting URL discovery for {self.start_url}")
        logger.info(f"Configuration: max_depth={self.max_depth}, same_domain_only={self.same_domain_only}, restrict_to_path={self.restrict_to_path}")
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                logger.info("Browser launched for URL discovery")
                
                while self.to_visit and len(self.discovered_urls) < self.max_pages:
                    current_url, depth = self.to_visit.pop(0)
                    
                    logger.info(f"Processing: {current_url} at depth {depth}, Discovered: {len(self.discovered_urls)}/{self.max_pages}")

                    # Skip if already visited
                    if current_url in self.visited_urls:
                        logger.info(f"Skipping already visited: {current_url}")
                        continue
                    
                    # Skip if beyond max depth
                    if depth > self.max_depth:
                        logger.info(f"Skipping beyond max depth: {current_url} (depth {depth} > {self.max_depth})")
                        continue
                    
                    # Check if we've hit the max pages limit
                    if len(self.discovered_urls) >= self.max_pages:
                        logger.info(f"Reached max pages limit: {self.max_pages}")
                        break

                    self.visited_urls.add(current_url)
                    
                    # Add current URL to discovered set (unless it's the start URL at depth 0)
                    if depth > 0:
                        self.discovered_urls.add(current_url)
                        logger.info(f"Added to discovered_urls: {current_url} (depth {depth})")
                    else:
                        logger.info(f"Start URL not added to results: {current_url} (depth {depth})")

                    # Visit page and extract links
                    try:
                        page = await browser.new_page()
                        await page.goto(current_url, timeout=settings.timeout, wait_until='networkidle')
                        page_content = await page.content()
                        await page.close()
                        
                        # Extract and add links if not at max depth
                        links_found = 0
                        if depth < self.max_depth:
                            links = self._extract_links_from_html(current_url, page_content)
                            links_found = len(links)
                            logger.info(f"Extracted {links_found} links from {current_url}")
                            for link in links:
                                if link not in self.visited_urls and (link, depth + 1) not in self.to_visit:
                                    self.to_visit.append((link, depth + 1))
                                    self.discovered_urls.add(link)
                                    logger.info(f"Added new link to queue: {link} at depth {depth + 1}")
                        else:
                            logger.info(f"At max depth, not extracting links from {current_url}")

                        logger.debug(f"Discovered {links_found} links from {current_url} at depth {depth}")

                    except Exception as e:
                        logger.warning(f"Error visiting {current_url}: {e}")
                        continue
                
                await browser.close()
                logger.info("Browser closed")
        
        except Exception as e:
            logger.error(f"URL discovery failed: {e}", exc_info=True)
            raise
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Sort URLs alphabetically
        sorted_urls = sorted(list(self.discovered_urls))
        
        logger.info(f"URL discovery completed: Found {len(sorted_urls)} unique URLs in {duration:.2f} seconds")
        
        return {
            "start_url": self.start_url,
            "discovered_urls": sorted_urls,
            "total_discovered": len(sorted_urls),
            "depth_crawled": self.max_depth,
            "duration_seconds": round(duration, 2),
            "same_domain_only": self.same_domain_only,
            "restrict_to_path": self.restrict_to_path,
            "status": "completed",
            "discovered_at": end_time.isoformat()
        }

    def _extract_links_from_html(self, current_url: str, html: str) -> List[str]:
        """
        Extract and normalize links from HTML content.
        
        Args:
            current_url: The URL of the current page
            html: HTML content to extract links from
            
        Returns:
            List of normalized, filtered URLs
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        all_hrefs = soup.find_all('a', href=True)
        print(f"DEBUG: Found {len(all_hrefs)} total <a> tags on {current_url}")

        for link in all_hrefs:
            href = link['href']
            
            # Skip javascript:, mailto:, tel:, etc.
            if href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
            
            # Normalize URL
            absolute_url = urljoin(current_url, href)
            normalized_url = self._normalize_url(absolute_url)
            
            print(f"DEBUG: Checking {href} -> {normalized_url}")

            if normalized_url and self._should_include_url(normalized_url):
                links.append(normalized_url)
                print(f"DEBUG: INCLUDED {normalized_url}")
            else:
                print(f"DEBUG: EXCLUDED {normalized_url}")

        print(f"DEBUG: Returning {len(links)} links after filtering")
        return links

    @staticmethod
    def _normalize_url(url: str) -> str:
        """
        Normalize URL by removing fragments and query parameters.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL or empty string if invalid
        """
        try:
            parsed = urlparse(url)
            # Remove fragment and query string for URL deduplication
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            # Remove trailing slash for consistency
            if normalized.endswith('/') and len(parsed.path) > 1:
                normalized = normalized.rstrip('/')
            return normalized
        except Exception:
            return ""

    def _should_include_url(self, url: str) -> bool:
        """
        Check if URL should be included based on domain and path restrictions.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL should be included
        """
        try:
            parsed = urlparse(url)
            
            # Check same domain (normalize www. subdomain)
            if self.same_domain_only:
                url_domain_normalized = parsed.netloc.replace('www.', '') if parsed.netloc.startswith('www.') else parsed.netloc
                if url_domain_normalized != self.domain_normalized:
                    return False

            # Check path restriction
            if self.restrict_to_path:
                if self.start_path and not parsed.path.startswith(self.start_path):
                    return False

            # Skip common non-content files
            skip_extensions = {
                '.pdf', '.zip', '.exe', '.dmg', '.pkg',
                '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico',
                '.css', '.js', '.json', '.xml',
                '.mp4', '.avi', '.mov', '.wmv',
                '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
            }
            
            path_lower = parsed.path.lower()
            if any(path_lower.endswith(ext) for ext in skip_extensions):
                return False
            
            return True
            
        except Exception:
            return False



async def discover_urls(
    url: str,
    max_depth: int = 2,
    max_pages: int = 100,
    same_domain_only: bool = True,
    restrict_to_path: bool = True
) -> Dict:
    """
    Discover URLs on a website.
    
    Args:
        url: Starting URL
        max_depth: Maximum crawl depth (1-10)
        max_pages: Maximum pages to discover (1-10000)
        same_domain_only: Only discover URLs on same domain
        restrict_to_path: Only discover URLs within starting path

    Returns:
        Dictionary containing discovered URLs and metadata
    """
    discoverer = URLDiscoverer(
        start_url=url,
        max_depth=max_depth,
        max_pages=max_pages,
        same_domain_only=same_domain_only,
        restrict_to_path=restrict_to_path
    )
    
    return await discoverer.discover()

