Create an AODA compliance checker that crawls a website and generates accessibility reports.
# Suggested libraries
- Scrapy or BeautifulSoup for crawling
- axe-core-python or playwright with axe for WCAG AA testing
- pandas for data aggregation
- reportlab or weasyprint for PDF reports

# Requirements
- The tool must have a web interface with a simple, user freindly UI.
- The tool must also be able to run with command line.

# Recommenrdations
-  Use software engineering principles.
- Use throttling when required for huge sites.
- To avoid using too many tokens at a time, build the application gradually by adding one feature at a time.
- Sugget any other libraires that should be used. For example, should this be built using FastAPI?