#!/usr/bin/env python3
"""
Example: Using Path Restriction Feature

This demonstrates how to use the new path restriction feature
to scan only specific sections of a website.

Run this file to see examples of how the feature works.
To actually run scans, you need to install dependencies first.
"""


def show_examples():
    """Display usage examples"""
    print("\n" + "=" * 60)
    print("PATH RESTRICTION FEATURE - Usage Examples")
    print("=" * 60 + "\n")

    print("=" * 60)
    print("Example 1: Path Restriction ENABLED (default)")
    print("=" * 60)
    print("Starting URL: https://yorku.ca/uit")
    print("Path restriction: True (default)")
    print("\nThis will ONLY scan pages under /uit path")
    print("  ✅ Will scan: https://yorku.ca/uit/services")
    print("  ✅ Will scan: https://yorku.ca/uit/contact")
    print("  ❌ Will skip: https://yorku.ca/about")
    print("  ❌ Will skip: https://yorku.ca/news")
    print()

    print("=" * 60)
    print("Example 2: Path Restriction DISABLED")
    print("=" * 60)
    print("Starting URL: https://yorku.ca/uit")
    print("Path restriction: False (explicitly disabled)")
    print("\nThis will scan ALL pages on the domain")
    print("  ✅ Will scan: https://yorku.ca/uit/services")
    print("  ✅ Will scan: https://yorku.ca/about")
    print("  ✅ Will scan: https://yorku.ca/news")
    print()

    print("=" * 60)
    print("Example 3: Deeper Path Restriction")
    print("=" * 60)
    print("Starting URL: https://example.com/products/electronics/phones")
    print("Path restriction: True (default)")
    print("\nThis will ONLY scan pages under /products/electronics/phones")
    print("  ✅ Will scan: /products/electronics/phones/iphone")
    print("  ✅ Will scan: /products/electronics/phones/android")
    print("  ❌ Will skip: /products/electronics/laptops")
    print("  ❌ Will skip: /products/clothing")
    print()

    print("=" * 60)
    print("CLI Usage Examples:")
    print("=" * 60)
    print("\n# Default behavior (path restriction enabled):")
    print("python main.py scan --url https://yorku.ca/uit")
    print("\n# Explicitly enable path restriction:")
    print("python main.py scan --url https://yorku.ca/uit --restrict-to-path")
    print("\n# Disable path restriction (scan entire domain):")
    print("python main.py scan --url https://yorku.ca/uit --no-restrict-to-path")

    print("\n" + "=" * 60)
    print("Python API Usage:")
    print("=" * 60)
    print("""
from src.models import ScanRequest
from src.core import AccessibilityCrawler
import asyncio

# With path restriction (default)
scan_request = ScanRequest(
    url="https://yorku.ca/uit",
    max_pages=50,
    max_depth=3,
    restrict_to_path=True  # This is the default
)

crawler = AccessibilityCrawler(scan_request)
result = asyncio.run(crawler.crawl())

# Without path restriction
scan_request = ScanRequest(
    url="https://yorku.ca/uit",
    max_pages=50,
    max_depth=3,
    restrict_to_path=False  # Scan entire domain
)

crawler = AccessibilityCrawler(scan_request)
result = asyncio.run(crawler.crawl())
""")

    print("=" * 60)
    print("Web Interface:")
    print("=" * 60)
    print("""
1. Start the web server: python main.py web
2. Open http://localhost:8000 in your browser
3. Enter URL: https://yorku.ca/uit
4. The checkbox "Only scan pages within the starting URL's path" 
   is CHECKED by default
5. Uncheck it if you want to scan the entire domain
6. Click "Start Accessibility Scan"
""")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    show_examples()

