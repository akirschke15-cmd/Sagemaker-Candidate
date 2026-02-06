#!/usr/bin/env python3
"""
Configuration Test Script

Run this script to verify that the configuration is properly loaded
and all settings are accessible.

Usage:
    python test_config.py
"""

from pathlib import Path
import sys

# Add ats_app to path
sys.path.insert(0, str(Path(__file__).parent / "ats_app"))

try:
    from config import settings

    print("[OK] Configuration module loaded successfully!\n")

    print("=" * 60)
    print("CONFIGURATION VALUES")
    print("=" * 60)

    print("\nDatabase:")
    print(f"  DB_PATH: {settings.DB_PATH}")

    print("\nAI / LLM:")
    print(f"  ANTHROPIC_API_KEY: {'***' + settings.ANTHROPIC_API_KEY[-8:] if settings.ANTHROPIC_API_KEY else '(not set)'}")
    print(f"  AI_MODEL: {settings.AI_MODEL}")
    print(f"  AI_MAX_TOKENS: {settings.AI_MAX_TOKENS}")
    print(f"  AI_TIMEOUT_SECONDS: {settings.AI_TIMEOUT_SECONDS}")

    print("\nAWS Bedrock:")
    print(f"  AWS_REGION: {settings.AWS_REGION}")
    print(f"  BEDROCK_MODEL_ID: {settings.BEDROCK_MODEL_ID}")
    print(f"  BEDROCK_CONNECT_TIMEOUT: {settings.BEDROCK_CONNECT_TIMEOUT}")
    print(f"  BEDROCK_READ_TIMEOUT: {settings.BEDROCK_READ_TIMEOUT}")

    print("\nEmail / SMTP:")
    print(f"  SMTP_HOST: {settings.SMTP_HOST or '(not set)'}")
    print(f"  SMTP_PORT: {settings.SMTP_PORT}")
    print(f"  SMTP_USER: {settings.SMTP_USER or '(not set)'}")
    print(f"  SMTP_PASSWORD: {'***' if settings.SMTP_PASSWORD else '(not set)'}")
    print(f"  SMTP_FROM: {settings.SMTP_FROM or '(not set)'}")
    print(f"  SMTP_TIMEOUT_SECONDS: {settings.SMTP_TIMEOUT_SECONDS}")

    print("\nFile Uploads:")
    print(f"  UPLOAD_DIR: {settings.UPLOAD_DIR}")
    print(f"  MAX_RESUME_SIZE_MB: {settings.MAX_RESUME_SIZE_MB}")

    print("\nSession / Auth:")
    print(f"  SESSION_TIMEOUT_HOURS: {settings.SESSION_TIMEOUT_HOURS}")
    print(f"  SCORECARD_TOKEN_EXPIRY_HOURS: {settings.SCORECARD_TOKEN_EXPIRY_HOURS}")

    print("\nWebhooks:")
    print(f"  WEBHOOK_TIMEOUT_SECONDS: {settings.WEBHOOK_TIMEOUT_SECONDS}")

    print("\n" + "=" * 60)
    print("VALIDATION CHECKS")
    print("=" * 60)

    warnings = []

    # Check critical settings
    if not settings.ANTHROPIC_API_KEY:
        warnings.append("[WARN]  ANTHROPIC_API_KEY is not set (AI features will not work)")

    if not settings.SMTP_HOST:
        warnings.append("[WARN]  SMTP_HOST is not set (email features will run in preview mode)")

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        warnings.append("[WARN]  SMTP credentials not set (email features will run in preview mode)")

    # Check paths exist
    db_path = Path(settings.DB_PATH)
    if not db_path.parent.exists():
        warnings.append(f"[WARN]  Database parent directory does not exist: {db_path.parent}")

    upload_dir = Path(settings.UPLOAD_DIR)
    if not upload_dir.exists():
        warnings.append(f"[WARN]  Upload directory does not exist (will be created on first upload): {upload_dir}")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  {warning}")
    else:
        print("\n[OK] All critical settings are configured!")

    print("\n" + "=" * 60)
    print("Configuration implementation:", type(settings).__name__)
    try:
        from pydantic_settings import BaseSettings
        print("Using pydantic-settings for enhanced validation")
    except ImportError:
        print("Using fallback implementation (install pydantic-settings for validation)")
    print("=" * 60)

    print("\n[OK] Configuration test completed successfully!")
    sys.exit(0)

except ImportError as e:
    print(f"[ERROR] Failed to import config module: {e}")
    print("\nMake sure you're running this from the ats_app directory:")
    print("  cd ats_app")
    print("  python test_config.py")
    sys.exit(1)

except Exception as e:
    print(f"[ERROR] Error during configuration test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
