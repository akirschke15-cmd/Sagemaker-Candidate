"""
Run the FastAPI server alongside the Streamlit app

This script initializes the database and starts the FastAPI server.
It can be run independently of the Streamlit application.

Usage:
    python run_api.py

    Or with custom host/port:
    API_HOST=127.0.0.1 API_PORT=8080 python run_api.py

Environment Variables:
    API_KEY: API key for authentication (optional, dev mode if empty)
    API_HOST: Host to bind to (default: 0.0.0.0)
    API_PORT: Port to listen on (default: 8000)
"""
import uvicorn
from api import app
from config import settings
from database import init_db, migrate_db


def main():
    """Initialize database and start FastAPI server"""
    print("Initializing ATS API Server...")
    print(f"API Host: {settings.API_HOST}")
    print(f"API Port: {settings.API_PORT}")
    print(f"API Key Auth: {'Enabled' if settings.API_KEY else 'Disabled (dev mode)'}")
    print("-" * 50)

    # Initialize database
    print("Initializing database...")
    init_db()
    migrate_db()
    print("Database ready.")

    # Start API server
    print(f"Starting API server on http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"API Documentation available at: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    print("-" * 50)

    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="info"
    )


if __name__ == "__main__":
    main()
