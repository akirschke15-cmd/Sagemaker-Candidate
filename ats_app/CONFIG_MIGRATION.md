# Configuration Migration Guide

## Overview

The ATS application now uses centralized configuration management through `config.py`. All environment variables and hardcoded configuration values have been consolidated into a single, type-safe configuration module.

## Files Created

### 1. `ats_app/config.py`
Centralized configuration module with two implementations:
- **Primary**: Uses `pydantic-settings` for type validation and automatic .env file loading
- **Fallback**: Simple class-based implementation if pydantic-settings is not installed

### 2. `.env.example`
Template file documenting all available configuration options with descriptions and defaults.

## Configuration Settings

### Database
- `DB_PATH`: Path to SQLite database file (default: `ats_app/ats_data.db`)

### AI / LLM
- `ANTHROPIC_API_KEY`: Anthropic API key for Claude AI features
- `AI_MODEL`: Claude model to use (default: `claude-sonnet-4-5-20250929`)
- `AI_MAX_TOKENS`: Maximum tokens for AI responses (default: `1024`)
- `AI_TIMEOUT_SECONDS`: Timeout for AI API calls (default: `30.0`)

### AWS Bedrock
- `AWS_REGION`: AWS region for Bedrock (default: `us-east-1`)
- `BEDROCK_MODEL_ID`: Bedrock model ID (default: `anthropic.claude-sonnet-4-5-20250929-v1:0`)
- `BEDROCK_CONNECT_TIMEOUT`: Connection timeout in seconds (default: `10`)
- `BEDROCK_READ_TIMEOUT`: Read timeout in seconds (default: `30`)

### Email / SMTP
- `SMTP_HOST`: SMTP server hostname
- `SMTP_PORT`: SMTP server port (default: `587`)
- `SMTP_USER`: SMTP username
- `SMTP_PASSWORD`: SMTP password
- `SMTP_FROM`: From email address
- `SMTP_TIMEOUT_SECONDS`: SMTP timeout (default: `30`)

### File Uploads
- `UPLOAD_DIR`: Directory for uploaded resumes (default: `ats_app/uploads/resumes`)
- `MAX_RESUME_SIZE_MB`: Maximum resume file size (default: `10.0`)

### Session / Auth
- `SESSION_TIMEOUT_HOURS`: Session timeout (default: `2`)
- `SCORECARD_TOKEN_EXPIRY_HOURS`: Scorecard token expiry (default: `48`)

### Webhooks
- `WEBHOOK_TIMEOUT_SECONDS`: Webhook request timeout (default: `10`)

## Files Updated

### 1. `genai.py`
**Changes:**
- Removed hardcoded `ANTHROPIC_API_KEY` global variable
- Added `from config import settings`
- Updated `get_anthropic_client()` to use `settings.ANTHROPIC_API_KEY`
- Updated `get_bedrock_client()` to use `settings.AWS_REGION`, `settings.BEDROCK_CONNECT_TIMEOUT`, `settings.BEDROCK_READ_TIMEOUT`
- Updated `invoke_claude_api()` to use `settings.AI_MODEL` and `settings.AI_TIMEOUT_SECONDS`
- Updated `invoke_bedrock()` to use `settings.BEDROCK_MODEL_ID`

### 2. `email_automation.py`
**Changes:**
- Added `from config import settings`
- Updated `process_email_queue()` to use `settings.SMTP_HOST`, `settings.SMTP_PORT`, `settings.SMTP_USER`, `settings.SMTP_PASSWORD`, `settings.SMTP_FROM`
- Removed direct `os.environ.get()` calls

### 3. `email_utils.py`
**Changes:**
- Added `from config import settings`
- Updated `send_email()` to use `settings.SMTP_TIMEOUT_SECONDS`

### 4. `database.py`
**Changes:**
- Added `from config import settings`
- Updated `DB_PATH` to use `Path(settings.DB_PATH)`

### 5. `resume_parser.py`
**Changes:**
- Added `from config import settings`
- Updated `UPLOAD_DIR` to use `Path(settings.UPLOAD_DIR)`
- Updated `validate_file_size()` to use `settings.MAX_RESUME_SIZE_MB` as default

### 6. `mobile_scorecard.py`
**Changes:**
- Added `from config import settings`
- Updated `generate_scorecard_token()` to use `settings.SCORECARD_TOKEN_EXPIRY_HOURS` as default

### 7. `notifications.py`
**Changes:**
- Added `from config import settings`
- Updated `send_slack_notification()` and `send_teams_notification()` to use `settings.WEBHOOK_TIMEOUT_SECONDS`

## Setup Instructions

### For Development

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your actual values:**
   ```bash
   # Required for AI features
   ANTHROPIC_API_KEY=your-api-key-here

   # Required for email automation
   SMTP_HOST=smtp.gmail.com
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   SMTP_FROM=your-email@gmail.com
   ```

3. **Optional: Install pydantic-settings for enhanced validation:**
   ```bash
   pip install pydantic-settings
   ```
   If not installed, the fallback implementation will be used automatically.

### For Production

1. **Set environment variables directly** (recommended for production):
   ```bash
   export ANTHROPIC_API_KEY=your-api-key
   export SMTP_HOST=smtp.gmail.com
   # ... etc
   ```

2. **Or use a `.env` file** (ensure it's in `.gitignore`):
   ```bash
   # .env file in project root
   ANTHROPIC_API_KEY=production-key
   SMTP_HOST=production-smtp-server
   ```

## Migration Benefits

### Before
- Configuration scattered across multiple files
- Mix of environment variables and hardcoded values
- No type safety or validation
- Difficult to discover available settings
- No documentation of defaults

### After
- ✅ Single source of truth for all configuration
- ✅ Type-safe configuration with validation (when using pydantic-settings)
- ✅ Clear documentation of all settings in `.env.example`
- ✅ Consistent defaults across the application
- ✅ Easy to override settings via environment variables
- ✅ Backward compatible with existing environment variable names

## Testing

All configuration changes are backward compatible. Existing environment variables will continue to work as before.

To verify the configuration is working:

```python
from ats_app.config import settings

# Check configuration values
print(f"DB Path: {settings.DB_PATH}")
print(f"AI Model: {settings.AI_MODEL}")
print(f"Upload Dir: {settings.UPLOAD_DIR}")
```

## Notes

- The `.env` file should **never** be committed to version control
- Use `.env.example` as a template for new developers
- All settings have sensible defaults and can be overridden as needed
- The configuration is loaded once at import time for efficiency
