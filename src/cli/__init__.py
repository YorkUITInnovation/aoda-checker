"""Command-line interface for the AODA crawler."""
import click
import asyncio
import logging
from pathlib import Path

from src.core import AccessibilityCrawler
from src.models import ScanRequest
from src.utils import ReportGenerator
from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.command()
@click.option('--url', required=True, help='The URL to scan for accessibility issues')
@click.option('--max-pages', default=settings.max_pages_default, help='Maximum number of pages to scan')
@click.option('--max-depth', default=settings.max_depth_default, help='Maximum crawl depth')
@click.option('--output', default=None, help='Output PDF file path')
@click.option('--same-domain-only/--all-domains', default=True, help='Crawl only same domain links')
@click.option('--restrict-to-path/--no-restrict-to-path', default=True, help='Only scan pages within the starting URL\'s path')
def scan(url: str, max_pages: int, max_depth: int, output: str, same_domain_only: bool, restrict_to_path: bool):
    """Scan a website for AODA/WCAG AA accessibility compliance."""
    click.echo(f"🔍 Starting accessibility scan of: {url}")
    click.echo(f"📊 Max pages: {max_pages}, Max depth: {max_depth}")
    click.echo(f"🔒 Path restriction: {'Enabled' if restrict_to_path else 'Disabled'}")

    try:
        # Create scan request
        scan_request = ScanRequest(
            url=url,
            max_pages=max_pages,
            max_depth=max_depth,
            same_domain_only=same_domain_only,
            restrict_to_path=restrict_to_path
        )

        # Run the crawler
        crawler = AccessibilityCrawler(scan_request)
        scan_result = asyncio.run(crawler.crawl())

        # Display results
        click.echo(f"\n✅ Scan completed!")
        click.echo(f"📄 Pages scanned: {scan_result.pages_scanned}")
        click.echo(f"⚠️  Pages with violations: {scan_result.pages_with_violations}")
        click.echo(f"🚨 Total violations: {scan_result.total_violations}")

        violations_by_impact = scan_result.get_violations_by_impact()
        click.echo(f"\n📊 Violations by severity:")
        click.echo(f"   Critical: {violations_by_impact['critical']}")
        click.echo(f"   Serious:  {violations_by_impact['serious']}")
        click.echo(f"   Moderate: {violations_by_impact['moderate']}")
        click.echo(f"   Minor:    {violations_by_impact['minor']}")

        # Generate PDF report
        click.echo(f"\n📝 Generating PDF report...")
        report_gen = ReportGenerator()
        report_path = report_gen.generate_pdf(scan_result, output)
        click.echo(f"✅ Report saved to: {report_path}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    scan()

