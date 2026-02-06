"""Centralized logging configuration for ATS application."""
import logging
import logging.handlers
import os
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "ats.log"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()


def setup_logging():
    """Configure logging for the entire application.

    Call this once at application startup (in app.py).
    All modules using logging.getLogger(__name__) will inherit this config.
    """
    # Create log directory
    LOG_DIR.mkdir(exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Clear existing handlers to avoid duplicates on Streamlit reruns
    root_logger.handlers.clear()

    # Console handler (INFO+)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # File handler (DEBUG+, rotating)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("streamlit").setLevel(logging.WARNING)

    logging.getLogger(__name__).info("Logging configured: level=%s, file=%s", LOG_LEVEL, LOG_FILE)
