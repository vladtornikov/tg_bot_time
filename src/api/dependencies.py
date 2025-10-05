"""FastAPI dependencies."""
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session
from config.settings import get_settings

settings = get_settings()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async for session in get_session():
        yield session


def get_current_settings():
    """Get current settings dependency."""
    return settings


def verify_telegram_webhook(telegram_token: str = None):
    """Verify Telegram webhook token."""
    if not telegram_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Telegram token",
        )
    
    if telegram_token != settings.telegram_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram token",
        )
    
    return True


