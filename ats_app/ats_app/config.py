"""Centralized configuration for ATS application."""
import os
from pathlib import Path
from typing import Optional

# Try pydantic-settings first, fall back to simple dataclass
try:
    from pydantic_settings import BaseSettings

    class Settings(BaseSettings):
        """Application settings with environment variable support."""

        # Database
        DB_PATH: str = str(Path(__file__).parent / "ats_data.db")
        DATABASE_URL: str = ""  # e.g. "postgresql://user:pass@localhost/ats" or "" for SQLite
        DB_POOL_SIZE: int = 5
        DB_MAX_OVERFLOW: int = 10
        DB_POOL_TIMEOUT: int = 30

        # AI / LLM
        ANTHROPIC_API_KEY: str = ""
        AI_MODEL: str = "claude-sonnet-4-5-20250929"
        AI_MAX_TOKENS: int = 1024
        AI_TIMEOUT_SECONDS: float = 30.0

        # AWS Bedrock
        AWS_REGION: str = "us-east-1"
        BEDROCK_MODEL_ID: str = "anthropic.claude-sonnet-4-5-20250929-v1:0"
        BEDROCK_CONNECT_TIMEOUT: int = 10
        BEDROCK_READ_TIMEOUT: int = 30

        # Email / SMTP
        SMTP_HOST: str = ""
        SMTP_PORT: int = 587
        SMTP_USER: str = ""
        SMTP_PASSWORD: str = ""
        SMTP_FROM: str = ""
        SMTP_TIMEOUT_SECONDS: int = 30

        # File Uploads
        UPLOAD_DIR: str = str(Path(__file__).parent / "uploads" / "resumes")
        MAX_RESUME_SIZE_MB: float = 10.0

        # File Upload Security
        MAX_PDF_PAGES: int = 100
        MAX_DECOMPRESSED_SIZE_MB: float = 50.0
        MAX_FILENAME_LENGTH: int = 255

        # Session / Auth
        SESSION_TIMEOUT_HOURS: int = 2
        SCORECARD_TOKEN_EXPIRY_HOURS: int = 48
        SESSION_SECRET_KEY: str = ""  # Auto-generated if empty
        DEV_MODE: bool = False

        # Webhooks
        WEBHOOK_TIMEOUT_SECONDS: int = 10

        # Rate Limiting
        LOGIN_RATE_LIMIT: int = 5
        LOGIN_RATE_WINDOW: int = 900  # 15 minutes
        SCORECARD_RATE_LIMIT: int = 10
        SCORECARD_RATE_WINDOW: int = 3600  # 1 hour
        API_RATE_LIMIT: int = 60
        API_RATE_WINDOW: int = 60  # 1 minute

        # API
        API_KEY: str = ""
        API_HOST: str = "127.0.0.1"
        API_PORT: int = 8000

        # Caching
        CACHE_DEFAULT_TTL: int = 30
        CACHE_ANALYTICS_TTL: int = 300
        CACHE_AI_TTL: int = 3600
        CACHE_ENABLED: bool = True

        model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

except ImportError:
    # Fallback: simple class reading from env vars
    class Settings:
        """Application settings with environment variable support (fallback implementation)."""

        def __init__(self):
            # Database
            self.DB_PATH = os.environ.get('DB_PATH', str(Path(__file__).parent / "ats_data.db"))
            self.DATABASE_URL = os.environ.get('DATABASE_URL', '')
            self.DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', '5'))
            self.DB_MAX_OVERFLOW = int(os.environ.get('DB_MAX_OVERFLOW', '10'))
            self.DB_POOL_TIMEOUT = int(os.environ.get('DB_POOL_TIMEOUT', '30'))

            # AI / LLM
            self.ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
            self.AI_MODEL = os.environ.get('AI_MODEL', 'claude-sonnet-4-5-20250929')
            self.AI_MAX_TOKENS = int(os.environ.get('AI_MAX_TOKENS', '1024'))
            self.AI_TIMEOUT_SECONDS = float(os.environ.get('AI_TIMEOUT_SECONDS', '30.0'))

            # AWS Bedrock
            self.AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
            self.BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-sonnet-4-5-20250929-v1:0')
            self.BEDROCK_CONNECT_TIMEOUT = int(os.environ.get('BEDROCK_CONNECT_TIMEOUT', '10'))
            self.BEDROCK_READ_TIMEOUT = int(os.environ.get('BEDROCK_READ_TIMEOUT', '30'))

            # Email / SMTP
            self.SMTP_HOST = os.environ.get('SMTP_HOST', '')
            self.SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
            self.SMTP_USER = os.environ.get('SMTP_USER', '')
            self.SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
            self.SMTP_FROM = os.environ.get('SMTP_FROM', '')
            self.SMTP_TIMEOUT_SECONDS = int(os.environ.get('SMTP_TIMEOUT_SECONDS', '30'))

            # File Uploads
            self.UPLOAD_DIR = os.environ.get('UPLOAD_DIR', str(Path(__file__).parent / "uploads" / "resumes"))
            self.MAX_RESUME_SIZE_MB = float(os.environ.get('MAX_RESUME_SIZE_MB', '10.0'))

            # File Upload Security
            self.MAX_PDF_PAGES = int(os.environ.get('MAX_PDF_PAGES', '100'))
            self.MAX_DECOMPRESSED_SIZE_MB = float(os.environ.get('MAX_DECOMPRESSED_SIZE_MB', '50.0'))
            self.MAX_FILENAME_LENGTH = int(os.environ.get('MAX_FILENAME_LENGTH', '255'))

            # Session / Auth
            self.SESSION_TIMEOUT_HOURS = int(os.environ.get('SESSION_TIMEOUT_HOURS', '2'))
            self.SCORECARD_TOKEN_EXPIRY_HOURS = int(os.environ.get('SCORECARD_TOKEN_EXPIRY_HOURS', '48'))
            self.SESSION_SECRET_KEY = os.environ.get('SESSION_SECRET_KEY', '')  # Auto-generated if empty
            self.DEV_MODE = os.environ.get('DEV_MODE', '').lower() in ('true', '1', 'yes')

            # Webhooks
            self.WEBHOOK_TIMEOUT_SECONDS = int(os.environ.get('WEBHOOK_TIMEOUT_SECONDS', '10'))

            # Rate Limiting
            self.LOGIN_RATE_LIMIT = int(os.environ.get('LOGIN_RATE_LIMIT', '5'))
            self.LOGIN_RATE_WINDOW = int(os.environ.get('LOGIN_RATE_WINDOW', '900'))  # 15 minutes
            self.SCORECARD_RATE_LIMIT = int(os.environ.get('SCORECARD_RATE_LIMIT', '10'))
            self.SCORECARD_RATE_WINDOW = int(os.environ.get('SCORECARD_RATE_WINDOW', '3600'))  # 1 hour
            self.API_RATE_LIMIT = int(os.environ.get('API_RATE_LIMIT', '60'))
            self.API_RATE_WINDOW = int(os.environ.get('API_RATE_WINDOW', '60'))  # 1 minute

            # API
            self.API_KEY = os.environ.get('API_KEY', '')
            self.API_HOST = os.environ.get('API_HOST', '127.0.0.1')
            self.API_PORT = int(os.environ.get('API_PORT', '8000'))

            # Caching
            self.CACHE_DEFAULT_TTL = int(os.environ.get('CACHE_DEFAULT_TTL', '30'))
            self.CACHE_ANALYTICS_TTL = int(os.environ.get('CACHE_ANALYTICS_TTL', '300'))
            self.CACHE_AI_TTL = int(os.environ.get('CACHE_AI_TTL', '3600'))
            self.CACHE_ENABLED = os.environ.get('CACHE_ENABLED', '').lower() not in ('false', '0', 'no')

# Singleton instance
settings = Settings()

# Startup security warnings
import logging as _logging
_startup_logger = _logging.getLogger(__name__)
if not settings.API_KEY:
    _startup_logger.warning("API_KEY is not configured. The REST API will reject all requests. Set API_KEY in .env.")
if not settings.SESSION_SECRET_KEY and not settings.DEV_MODE:
    _startup_logger.warning("SESSION_SECRET_KEY not configured. Sessions will be invalidated on restart. Set SESSION_SECRET_KEY in .env.")
