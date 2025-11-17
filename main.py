"""Main entry point for the AODA Compliance Checker."""
import click
import uvicorn
from pathlib import Path

from src.config import settings


@click.group()
def cli():
    """AODA Compliance Checker - Scan websites for accessibility issues."""
    pass


@cli.command()
@click.option('--host', default=settings.host, help='Host to bind to')
@click.option('--port', default=settings.port, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
def web(host: str, port: int, reload: bool):
    """Start the web interface."""
    click.echo(f"🚀 Starting AODA Compliance Checker web interface...")
    click.echo(f"📍 Server running at http://{host}:{port}")
    click.echo(f"Press CTRL+C to quit")

    # Create necessary directories
    Path("reports").mkdir(exist_ok=True)
    Path("static").mkdir(exist_ok=True)

    uvicorn.run(
        "src.web.app:app",
        host=host,
        port=port,
        reload=reload
    )


@cli.command()
@click.option('--url', required=True, help='The URL to scan')
@click.option('--max-pages', default=settings.max_pages_default, help='Maximum pages to scan')
@click.option('--max-depth', default=settings.max_depth_default, help='Maximum crawl depth')
@click.option('--output', default=None, help='Output PDF file path')
@click.option('--same-domain-only/--all-domains', default=True, help='Crawl only same domain')
@click.option('--restrict-to-path/--no-restrict-to-path', default=True, help='Only scan pages within the starting URL\'s path')
def scan(url: str, max_pages: int, max_depth: int, output: str, same_domain_only: bool, restrict_to_path: bool):
    """Run a scan from the command line."""
    from src.cli import scan as cli_scan

    # Import here to avoid circular imports
    import sys
    sys.argv = [
        'scan',
        '--url', url,
        '--max-pages', str(max_pages),
        '--max-depth', str(max_depth),
    ]
    if output:
        sys.argv.extend(['--output', output])
    if same_domain_only:
        sys.argv.append('--same-domain-only')
    else:
        sys.argv.append('--all-domains')
    if restrict_to_path:
        sys.argv.append('--restrict-to-path')
    else:
        sys.argv.append('--no-restrict-to-path')

    cli_scan()


if __name__ == '__main__':
    cli()

