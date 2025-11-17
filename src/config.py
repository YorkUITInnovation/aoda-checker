"""Configuration settings for the AODA crawler."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "AODA Compliance Checker"
    app_version: str = "1.0.0"

    # Security
    secret_key: str = "change-this-secret-key-in-production"  # Used for sessions and JWT
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 480  # 8 hours

    # Timezone
    timezone: str = "America/Toronto"  # Timezone for timestamps (configurable via TZ or TIMEZONE env var)

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Crawler settings
    max_pages_default: int = 50
    max_depth_default: int = 3
    request_delay: float = 0.2  # Seconds between requests (configurable via REQUEST_DELAY env var)
    timeout: int = 20000  # Milliseconds (configurable via TIMEOUT env var)

    # Screenshot settings (major performance impact)
    enable_screenshots: bool = False  # Disabled by default for faster scans (configurable via ENABLE_SCREENSHOTS)
    max_screenshots_per_page: int = 5  # Limit screenshots even when enabled (configurable via MAX_SCREENSHOTS_PER_PAGE)

    # Report settings
    reports_dir: str = "reports"

    # Database settings
    database_url: str = "mysql+aiomysql://aoda_user:aoda_password@localhost:3306/aoda_checker"
    database_echo: bool = False  # Set to True to see SQL queries in logs

    # MySQL connection pool settings
    db_pool_size: int = 10
    db_max_overflow: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

