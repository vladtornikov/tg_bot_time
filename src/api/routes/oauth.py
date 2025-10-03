"""OAuth endpoints for calendar provider authentication."""
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from urllib.parse import urlencode, parse_qs

from fastapi import APIRouter, HTTPException, Query, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database.session import get_session
from models.user import User
from models.oauth import OAuthToken
from providers.google import GoogleCalendarProvider
from utils.encryption import encryption_service
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Create router
router = APIRouter(prefix="/oauth", tags=["oauth"])

# OAuth state storage (in production, use Redis)
oauth_states = {}


@router.get("/google/start")
async def oauth_start(
    user_id: int = Query(..., description="Telegram user ID"),
    redirect_uri: Optional[str] = Query(None, description="Redirect URI after OAuth"),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Start OAuth flow for Google Calendar access.
    
    Args:
        user_id: Telegram user ID
        redirect_uri: Optional redirect URI after OAuth completion
        
    Returns:
        OAuth authorization URL and state
    """
    try:
        # Validate user exists
        user = await get_user_by_telegram_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Generate OAuth state
        state = secrets.token_urlsafe(32)
        
        # Store state with user info
        oauth_states[state] = {
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "redirect_uri": redirect_uri,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
        }
        
        # Create Google Calendar provider
        google_provider = GoogleCalendarProvider()
        
        # Generate authorization URL
        auth_url = await google_provider.get_oauth_authorization_url(
            user_id=user.id,
            redirect_uri=settings.google_redirect_uri,
            state=state,
        )
        
        logger.info(f"OAuth started for user {user_id}, state: {state}")
        
        return {
            "authorization_url": auth_url,
            "state": state,
            "expires_in": 600,  # 10 minutes
        }
        
    except Exception as e:
        logger.error(f"OAuth start error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start OAuth flow")


@router.get("/google/callback")
async def oauth_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="OAuth state"),
    error: Optional[str] = Query(None, description="OAuth error"),
    db: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    """
    Handle OAuth callback from Google Calendar.
    
    Args:
        code: Authorization code from Google
        state: OAuth state parameter
        error: Optional error parameter
        
    Returns:
        Redirect response to success or error page
    """
    try:
        # Check for OAuth error
        if error:
            logger.warning(f"OAuth error: {error}")
            return RedirectResponse(
                url=f"https://t.me/your_bot?start=oauth_error_{error}",
                status_code=302
            )
        
        # Validate state
        if state not in oauth_states:
            logger.warning(f"Invalid OAuth state: {state}")
            return RedirectResponse(
                url="https://t.me/your_bot?start=oauth_error_invalid_state",
                status_code=302
            )
        
        state_data = oauth_states[state]
        
        # Check state expiration
        if datetime.now(timezone.utc) > state_data["expires_at"]:
            logger.warning(f"Expired OAuth state: {state}")
            del oauth_states[state]
            return RedirectResponse(
                url="https://t.me/your_bot?start=oauth_error_expired",
                status_code=302
            )
        
        # Get user
        user = await get_user_by_id(db, state_data["user_id"])
        if not user:
            logger.error(f"User not found for OAuth state: {state}")
            return RedirectResponse(
                url="https://t.me/your_bot?start=oauth_error_user_not_found",
                status_code=302
            )
        
        # Create Google Calendar provider
        google_provider = GoogleCalendarProvider()
        
        # Exchange code for token
        token_data = await google_provider.exchange_code_for_token(
            code=code,
            redirect_uri=settings.google_redirect_uri,
            state=state,
        )
        
        # Encrypt tokens
        encrypted_access_token = encryption_service.encrypt(token_data["access_token"])
        encrypted_refresh_token = None
        if token_data.get("refresh_token"):
            encrypted_refresh_token = encryption_service.encrypt(token_data["refresh_token"])
        
        # Calculate expiration
        expires_at = None
        if token_data.get("expires_in"):
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
        
        # Check for existing OAuth token
        existing_token = await get_oauth_token(db, user.id, "google")
        
        if existing_token:
            # Update existing token
            existing_token.access_token = encrypted_access_token
            existing_token.refresh_token = encrypted_refresh_token
            existing_token.expires_at = expires_at
            existing_token.scope = token_data.get("scope", "")
            existing_token.is_active = True
            existing_token.updated_at = datetime.now(timezone.utc)
        else:
            # Create new token
            oauth_token = OAuthToken(
                user_id=user.id,
                provider="google",
                access_token=encrypted_access_token,
                refresh_token=encrypted_refresh_token,
                expires_at=expires_at,
                scope=token_data.get("scope", ""),
                is_active=True,
            )
            db.add(oauth_token)
        
        # Commit changes
        await db.commit()
        
        # Clean up state
        del oauth_states[state]
        
        logger.info(f"OAuth completed successfully for user {user.telegram_id}")
        
        # Redirect to success page
        redirect_uri = state_data.get("redirect_uri", "https://t.me/your_bot?start=oauth_success")
        return RedirectResponse(url=redirect_uri, status_code=302)
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        return RedirectResponse(
            url="https://t.me/your_bot?start=oauth_error_server",
            status_code=302
        )


@router.post("/google/refresh")
async def oauth_refresh(
    user_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Refresh OAuth token for Google Calendar.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Token refresh status
    """
    try:
        # Get user
        user = await get_user_by_telegram_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get OAuth token
        oauth_token = await get_oauth_token(db, user.id, "google")
        if not oauth_token:
            raise HTTPException(status_code=404, detail="OAuth token not found")
        
        if not oauth_token.refresh_token:
            raise HTTPException(status_code=400, detail="No refresh token available")
        
        # Create Google Calendar provider
        google_provider = GoogleCalendarProvider()
        
        # Refresh token
        token_data = await google_provider.refresh_access_token(
            refresh_token=encryption_service.decrypt(oauth_token.refresh_token)
        )
        
        # Update token
        oauth_token.access_token = encryption_service.encrypt(token_data["access_token"])
        if token_data.get("expires_in"):
            oauth_token.expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=token_data["expires_in"]
            )
        oauth_token.updated_at = datetime.now(timezone.utc)
        
        # Commit changes
        await db.commit()
        
        logger.info(f"OAuth token refreshed for user {user.telegram_id}")
        
        return {
            "success": True,
            "expires_at": oauth_token.expires_at.isoformat() if oauth_token.expires_at else None,
        }
        
    except Exception as e:
        logger.error(f"OAuth refresh error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to refresh token")


@router.get("/google/status")
async def oauth_status(
    user_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Check OAuth token status for Google Calendar.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        OAuth token status
    """
    try:
        # Get user
        user = await get_user_by_telegram_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get OAuth token
        oauth_token = await get_oauth_token(db, user.id, "google")
        if not oauth_token:
            return {
                "connected": False,
                "status": "not_connected",
                "message": "No OAuth token found",
            }
        
        # Check token status
        if not oauth_token.is_active:
            return {
                "connected": False,
                "status": "inactive",
                "message": "OAuth token is inactive",
            }
        
        if oauth_token.is_expired:
            return {
                "connected": False,
                "status": "expired",
                "message": "OAuth token is expired",
                "expires_at": oauth_token.expires_at.isoformat() if oauth_token.expires_at else None,
            }
        
        # Check if token needs refresh
        if oauth_token.needs_refresh:
            return {
                "connected": True,
                "status": "needs_refresh",
                "message": "OAuth token needs refresh",
                "expires_at": oauth_token.expires_at.isoformat() if oauth_token.expires_at else None,
            }
        
        return {
            "connected": True,
            "status": "active",
            "message": "OAuth token is active",
            "expires_at": oauth_token.expires_at.isoformat() if oauth_token.expires_at else None,
        }
        
    except Exception as e:
        logger.error(f"OAuth status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to check OAuth status")


@router.delete("/google/disconnect")
async def oauth_disconnect(
    user_id: int = Query(..., description="Telegram user ID"),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Disconnect OAuth token for Google Calendar.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Disconnection status
    """
    try:
        # Get user
        user = await get_user_by_telegram_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get OAuth token
        oauth_token = await get_oauth_token(db, user.id, "google")
        if not oauth_token:
            raise HTTPException(status_code=404, detail="OAuth token not found")
        
        # Deactivate token
        oauth_token.is_active = False
        oauth_token.updated_at = datetime.now(timezone.utc)
        
        # Commit changes
        await db.commit()
        
        logger.info(f"OAuth disconnected for user {user.telegram_id}")
        
        return {
            "success": True,
            "message": "OAuth token disconnected successfully",
        }
        
    except Exception as e:
        logger.error(f"OAuth disconnect error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to disconnect OAuth token")


# Helper functions
async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[User]:
    """Get user by Telegram ID."""
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_oauth_token(db: AsyncSession, user_id: int, provider: str) -> Optional[OAuthToken]:
    """Get OAuth token for user and provider."""
    stmt = select(OAuthToken).where(
        and_(OAuthToken.user_id == user_id, OAuthToken.provider == provider)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
