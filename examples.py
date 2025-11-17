"""
Example usage of the AODA Compliance Checker API.

This demonstrates how to use the crawler programmatically.
"""
import asyncio
from src.core import AccessibilityCrawler
from src.models import ScanRequest
from src.utils import ReportGenerator


async def example_scan():
    """Example: Run a scan programmatically."""
    print("🔍 AODA Compliance Checker - Programmatic Example\n")

    # Create a scan request
    scan_request = ScanRequest(
        url="https://example.com",
        max_pages=5,
        max_depth=2,
        same_domain_only=True
    )

    print(f"Starting scan of: {scan_request.url}")
    print(f"Max pages: {scan_request.max_pages}")
    print(f"Max depth: {scan_request.max_depth}\n")

    # Create and run the crawler
    crawler = AccessibilityCrawler(scan_request)
    scan_result = await crawler.crawl()

    # Display results
    print("\n" + "="*60)
    print("SCAN RESULTS")
    print("="*60)
    print(f"Status: {scan_result.status}")
    print(f"Pages scanned: {scan_result.pages_scanned}")
    print(f"Pages with violations: {scan_result.pages_with_violations}")
    print(f"Total violations: {scan_result.total_violations}")
    print(f"Duration: {scan_result.duration:.2f} seconds")

    # Show violations by impact
    violations_by_impact = scan_result.get_violations_by_impact()
    print(f"\nViolations by severity:")
    print(f"  Critical: {violations_by_impact['critical']}")
    print(f"  Serious:  {violations_by_impact['serious']}")
    print(f"  Moderate: {violations_by_impact['moderate']}")
    print(f"  Minor:    {violations_by_impact['minor']}")

    # Show detailed results for each page
    print(f"\n" + "="*60)
    print("DETAILED RESULTS")
    print("="*60)

    for page in scan_result.page_results:
        print(f"\n📄 {page.url}")
        if page.title:
            print(f"   Title: {page.title}")

        if page.error:
            print(f"   ❌ Error: {page.error}")
        elif page.has_violations:
            print(f"   ⚠️  Violations: {page.violation_count}")

            # Show first 3 violations
            for i, violation in enumerate(page.violations[:3], 1):
                print(f"\n   {i}. [{violation.impact.value.upper()}] {violation.help}")
                print(f"      {violation.description}")

            if len(page.violations) > 3:
                print(f"\n   ... and {len(page.violations) - 3} more violations")
        else:
            print(f"   ✅ No violations found!")

    # Generate PDF report
    print(f"\n" + "="*60)
    print("GENERATING REPORT")
    print("="*60)

    report_gen = ReportGenerator()
    report_path = report_gen.generate_pdf(scan_result)
    print(f"✅ PDF report saved to: {report_path}")

    return scan_result


async def example_custom_config():
    """Example: Scan with custom configuration."""
    print("\n🔧 Example: Custom configuration scan\n")

    # Scan with custom settings
    scan_request = ScanRequest(
        url="https://example.com",
        max_pages=10,
        max_depth=1,
        same_domain_only=False  # Crawl external links too
    )

    crawler = AccessibilityCrawler(scan_request)
    scan_result = await crawler.crawl()

    print(f"Scanned {scan_result.pages_scanned} pages")
    print(f"Found {scan_result.total_violations} violations")

    return scan_result


def example_model_usage():
    """Example: Working with data models."""
    print("\n📊 Example: Data model usage\n")

    from src.models import PageResult, AccessibilityViolation, ViolationImpact

    # Create a page result
    page = PageResult(
        url="https://example.com",
        title="Example Page"
    )

    # Add a violation
    violation = AccessibilityViolation(
        id="color-contrast",
        impact=ViolationImpact.SERIOUS,
        description="Elements must have sufficient color contrast",
        help="Ensure all text has sufficient color contrast",
        help_url="https://dequeuniversity.com/rules/axe/4.0/color-contrast",
        tags=["wcag2aa", "wcag143"]
    )

    page.violations.append(violation)

    # Access properties
    print(f"Page URL: {page.url}")
    print(f"Has violations: {page.has_violations}")
    print(f"Violation count: {page.violation_count}")
    print(f"First violation: {page.violations[0].help}")

    # Convert to dict
    page_dict = page.model_dump()
    print(f"\nPage as dict: {list(page_dict.keys())}")

    # Convert to JSON
    page_json = page.model_dump_json(indent=2)
    print(f"\nPage as JSON (first 200 chars):\n{page_json[:200]}...")


if __name__ == "__main__":
    print("AODA Compliance Checker - Usage Examples")
    print("=" * 60 + "\n")

    # Example 1: Basic scan
    asyncio.run(example_scan())

    # Example 2: Custom configuration
    # Uncomment to run:
    # asyncio.run(example_custom_config())

    # Example 3: Model usage
    example_model_usage()

    print("\n" + "=" * 60)
    print("✅ Examples complete!")
    print("\nFor more information:")
    print("  - README.md: Project overview")
    print("  - USAGE.md: User guide")
    print("  - TECHNICAL.md: Technical documentation")

