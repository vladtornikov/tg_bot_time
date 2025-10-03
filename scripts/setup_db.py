#!/usr/bin/env python3
"""
Database setup script for development environment.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

from config.settings import get_settings


async def setup_database():
    """Set up the database for development."""
    settings = get_settings()
    
    # Create database if it doesn't exist
    sync_engine = create_engine(settings.database_url_sync)
    
    with sync_engine.connect() as conn:
        # Check if database exists
        result = conn.execute(text(
            "SELECT 1 FROM pg_database WHERE datname = 'tg_bot_dev'"
        ))
        
        if not result.fetchone():
            # Create database
            conn.execute(text("COMMIT"))
            conn.execute(text("CREATE DATABASE tg_bot_dev"))
            print("Database 'tg_bot_dev' created successfully")
        else:
            print("Database 'tg_bot_dev' already exists")
    
    # Run migrations
    import subprocess
    result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("Database migrations applied successfully")
    else:
        print(f"Migration failed: {result.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(setup_database())
