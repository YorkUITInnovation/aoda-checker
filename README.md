# AODA Compliance Checker

An automated AODA/WCAG AA compliance checker that crawls websites and generates accessibility reports.

> **🚀 New User?** See [QUICKSTART.md](QUICKSTART.md) for a 5-minute setup guide!

## Features

- ✅ Crawl websites and analyze accessibility
- ✅ WCAG 2.1 AA compliance testing using axe-core
- ✅ **Path restriction for focused scanning** (scan only specific sections like `/uit`)
- ✅ Web interface for easy use
- ✅ Command-line interface for automation
- ✅ PDF report generation
- ✅ Throttling for large sites
- ✅ MySQL 8.4 database integration for scan history
- ✅ Docker deployment with docker compose

## Installation

### Option 1: Docker (Recommended)

The easiest way to run the application with MySQL:

```bash
# Quick start (builds and starts everything)
./docker-quickstart.sh

# Or manually
docker compose up -d

# View logs
docker compose logs -f

# Access the application at http://localhost:8080
```
### Option 2: Local Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

5. (Optional) Setup MySQL database:
   ```bash
   # Install MySQL 8.4 locally
   # Create database
   mysql -u root -p < scripts/create_database.sql
   
   # Initialize tables
   python scripts/init_db.py
   ```

## Usage

### Web Interface

Start the web server:
```bash
python main.py web
```

Then open your browser to `http://localhost:8000`

### Command Line

Run a scan from the command line:
```bash
python main.py scan --url https://example.com --max-pages 10 --output report.pdf
```

## Project Structure

```
aoda_crawler/
├── src/
│   ├── core/                    # Core crawler and testing logic
│   │   ├── __init__.py
│   │   └── crawler.py          # AccessibilityCrawler class
│   ├── web/                     # FastAPI web interface
│   │   ├── __init__.py
│   │   └── app.py              # FastAPI application
│   ├── cli/                     # Command-line interface
│   │   └── __init__.py         # Click CLI commands
│   ├── models/                  # Data models
│   │   └── __init__.py         # Pydantic models
│   ├── utils/                   # Utility functions
│   │   ├── __init__.py
│   │   └── report_generator.py # PDF report generation
│   └── config.py               # Configuration settings
├── templates/                   # Jinja2 HTML templates
│   ├── index.html              # Main page
│   └── results.html            # Results page
├── static/                      # Static files (CSS, JS)
├── tests/                       # Test suite
│   ├── __init__.py
│   └── test_basic.py           # Unit tests
├── reports/                     # Generated reports (auto-created)
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── setup.sh                    # Quick setup script
├── .env.example               # Environment config example
├── README.md                  # This file
├── USAGE.md                   # User guide
├── TECHNICAL.md               # Technical documentation
└── CHANGELOG.md               # Version history
```

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

## Technologies Used

- **FastAPI**: Modern, fast web framework for building APIs
- **Playwright**: Reliable browser automation
- **axe-core**: Industry-standard accessibility testing engine
- **Pydantic**: Data validation using Python type hints
- **Click**: Beautiful command-line interfaces
- **WeasyPrint**: Create PDF documents from HTML/CSS
- **Jinja2**: Template engine for Python
- **Uvicorn**: Lightning-fast ASGI server

## Features in Detail

### Accessibility Testing
- Tests for 90+ WCAG 2.1 Level AA compliance rules
- Four severity levels: Critical, Serious, Moderate, Minor
- Detailed violation descriptions with remediation guidance
- Links to WCAG documentation for each issue

### Smart Crawling
- Configurable depth and page limits
- URL normalization and deduplication
- Same-domain filtering option
- **Path restriction to scan specific site sections** (see [PATH_RESTRICTION.md](PATH_RESTRICTION.md))
- Respects throttling to avoid server overload
- Graceful error handling

### Reporting
- Beautiful PDF reports with color-coded violations
- Interactive web results page
- Real-time scan progress tracking
- Downloadable reports
- Executive summary with statistics

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup
```bash
# Clone the repository
git clone <repository-url>
cd aoda_crawler

# Run setup script
./setup.sh

# Install development dependencies
pip install -r requirements.txt pytest black flake8

# Run tests
pytest tests/ -v
```

## Roadmap

See [CHANGELOG.md](CHANGELOG.md) for planned features including:
- User authentication
- Scheduled scans with notifications
- Comparison reports
- JSON/CSV export options

## Support

For detailed usage instructions, see [USAGE.md](USAGE.md).

For technical details and architecture, see [TECHNICAL.md](TECHNICAL.md).

## Acknowledgments

- Built with [axe-core](https://github.com/dequelabs/axe-core) by Deque Systems
- WCAG guidelines by W3C
- Inspired by the need for accessible web experiences

## Author

Patrick Thibaudeau

## License

MIT

