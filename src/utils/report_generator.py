"""Report generation functionality."""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    WEASYPRINT_AVAILABLE = False
    logging.warning(f"WeasyPrint not available: {e}. PDF generation will be disabled.")
    HTML = None
    CSS = None

from jinja2 import Template

from src.models import ScanResult
from src.config import settings


class ReportGenerator:
    """Generate PDF reports from scan results."""

    def __init__(self):
        """Initialize the report generator."""
        self.reports_dir = Path(settings.reports_dir)
        self.reports_dir.mkdir(exist_ok=True)

    def generate_pdf(self, scan_result: ScanResult, output_path: Optional[str] = None) -> str:
        """Generate a PDF report from scan results."""
        if not WEASYPRINT_AVAILABLE:
            raise RuntimeError(
                "WeasyPrint is not available. PDF generation is disabled.\n"
                "To enable PDF generation, install system dependencies:\n"
                "  macOS: brew install pango gdk-pixbuf libffi cairo\n"
                "  Then: pip install --force-reinstall weasyprint"
            )

        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(self.reports_dir / f"accessibility_report_{timestamp}.pdf")

        # Generate HTML content
        html_content = self._generate_html(scan_result)

        # Convert to PDF - use simpler API to avoid version conflicts
        try:
            HTML(string=html_content).write_pdf(output_path)
        except Exception as e:
            logging.error(f"WeasyPrint PDF generation failed: {e}")
            # Fallback: save as HTML instead
            html_path = output_path.replace('.pdf', '.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return html_path

        return output_path

    def _generate_html(self, scan_result: ScanResult) -> str:
        """Generate HTML content for the report."""
        template = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Accessibility Report</title>
</head>
<body>
    <div class="header">
        <h1>AODA/WCAG 2.1 AA Compliance Report</h1>
        <div class="metadata">
            <p><strong>Website:</strong> {{ scan_result.start_url }}</p>
            <p><strong>Scan Date:</strong> {{ scan_result.start_time.strftime('%Y-%m-%d %H:%M:%S') }}</p>
            <p><strong>Duration:</strong> {{ "%.2f"|format(scan_result.duration or 0) }} seconds</p>
            <p><strong>Pages Scanned:</strong> {{ scan_result.pages_scanned }}</p>
        </div>
    </div>
    
    <div class="summary">
        <h2>Executive Summary</h2>
        <div class="stats-grid">
            <div class="stat-box critical">
                <div class="stat-number">{{ violations_by_impact.critical }}</div>
                <div class="stat-label">Critical Issues</div>
            </div>
            <div class="stat-box serious">
                <div class="stat-number">{{ violations_by_impact.serious }}</div>
                <div class="stat-label">Serious Issues</div>
            </div>
            <div class="stat-box moderate">
                <div class="stat-number">{{ violations_by_impact.moderate }}</div>
                <div class="stat-label">Moderate Issues</div>
            </div>
            <div class="stat-box minor">
                <div class="stat-number">{{ violations_by_impact.minor }}</div>
                <div class="stat-label">Minor Issues</div>
            </div>
        </div>
        <p class="summary-text">
            Out of {{ scan_result.pages_scanned }} pages scanned, 
            {{ scan_result.pages_with_violations }} pages have accessibility violations,
            with a total of {{ scan_result.total_violations }} issues found.
        </p>
    </div>
    
    <div class="details">
        <h2>Detailed Results</h2>
        {% for page in scan_result.page_results %}
        <div class="page-result">
            <h3>{{ page.url }}</h3>
            {% if page.title %}
            <p class="page-title">Page Title: {{ page.title }}</p>
            {% endif %}
            
            {% if page.error %}
            <div class="error-box">
                <strong>Error:</strong> {{ page.error }}
            </div>
            {% elif page.violations %}
            <p><strong>Violations Found:</strong> {{ page.violations|length }}</p>
            
            {% for violation in page.violations %}
            <div class="violation {{ violation.impact.value }}">
                <div class="violation-header">
                    <span class="impact-badge">{{ violation.impact.value.upper() }}</span>
                    <strong>{{ violation.help }}</strong>
                </div>
                <p>{{ violation.description }}</p>
                <p class="help-url"><a href="{{ violation.help_url }}">More info</a></p>
                <p class="tags">Tags: {{ violation.tags|join(', ') }}</p>
                {% if violation.nodes %}
                <p><strong>Affected elements:</strong> {{ violation.nodes|length }}</p>
                {% endif %}
            </div>
            {% endfor %}
            
            {% else %}
            <div class="success-box">
                ✓ No violations found on this page!
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    <div class="footer">
        <p>Generated by AODA Compliance Checker v1.0.0</p>
        <p>This report tests for WCAG 2.1 Level AA compliance using axe-core.</p>
    </div>
</body>
</html>
        """)

        violations_by_impact = scan_result.get_violations_by_impact()

        return template.render(
            scan_result=scan_result,
            violations_by_impact=violations_by_impact
        )

    def _get_css(self) -> str:
        """Get CSS styles for the PDF report."""
        return """
            @page {
                size: A4;
                margin: 2cm;
            }
            
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }
            
            .header {
                border-bottom: 3px solid #2c3e50;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }
            
            h1 {
                color: #2c3e50;
                margin: 0 0 20px 0;
            }
            
            h2 {
                color: #34495e;
                border-bottom: 2px solid #ecf0f1;
                padding-bottom: 10px;
                margin-top: 30px;
            }
            
            h3 {
                color: #555;
                font-size: 14px;
                margin-top: 20px;
                word-wrap: break-word;
            }
            
            .metadata p {
                margin: 5px 0;
            }
            
            .summary {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 5px;
                margin: 20px 0;
            }
            
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                margin: 20px 0;
            }
            
            .stat-box {
                background: white;
                padding: 15px;
                border-radius: 5px;
                text-align: center;
                border-left: 4px solid #ccc;
            }
            
            .stat-box.critical {
                border-left-color: #e74c3c;
            }
            
            .stat-box.serious {
                border-left-color: #e67e22;
            }
            
            .stat-box.moderate {
                border-left-color: #f39c12;
            }
            
            .stat-box.minor {
                border-left-color: #3498db;
            }
            
            .stat-number {
                font-size: 32px;
                font-weight: bold;
                color: #2c3e50;
            }
            
            .stat-label {
                font-size: 12px;
                color: #7f8c8d;
                margin-top: 5px;
            }
            
            .summary-text {
                margin-top: 15px;
                font-size: 14px;
            }
            
            .page-result {
                margin: 20px 0;
                padding: 15px;
                background: #fff;
                border: 1px solid #ddd;
                border-radius: 5px;
                page-break-inside: avoid;
            }
            
            .page-title {
                color: #7f8c8d;
                font-style: italic;
            }
            
            .violation {
                margin: 15px 0;
                padding: 15px;
                border-left: 4px solid #ccc;
                background: #f8f9fa;
                page-break-inside: avoid;
            }
            
            .violation.critical {
                border-left-color: #e74c3c;
                background: #fadbd8;
            }
            
            .violation.serious {
                border-left-color: #e67e22;
                background: #fdebd0;
            }
            
            .violation.moderate {
                border-left-color: #f39c12;
                background: #fcf3cf;
            }
            
            .violation.minor {
                border-left-color: #3498db;
                background: #d6eaf8;
            }
            
            .violation-header {
                margin-bottom: 10px;
            }
            
            .impact-badge {
                display: inline-block;
                padding: 3px 8px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
                color: white;
                background: #95a5a6;
                margin-right: 10px;
            }
            
            .help-url {
                font-size: 12px;
            }
            
            .help-url a {
                color: #3498db;
                text-decoration: none;
            }
            
            .tags {
                font-size: 11px;
                color: #7f8c8d;
            }
            
            .success-box {
                padding: 15px;
                background: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
                border-radius: 5px;
            }
            
            .error-box {
                padding: 15px;
                background: #f8d7da;
                border: 1px solid #f5c6cb;
                color: #721c24;
                border-radius: 5px;
            }
            
            .footer {
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                font-size: 12px;
                color: #7f8c8d;
                text-align: center;
            }
        """

