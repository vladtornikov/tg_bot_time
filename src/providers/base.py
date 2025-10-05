"""Base calendar provider interface."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from models.user import User
from models.oauth import OAuthToken


class CalendarProvider(ABC):
    """Abstract base class for calendar providers."""
    
    def __init__(self, provider_name: str):
        """Initialize calendar provider."""
        self.provider_name = provider_name
    
    @abstractmethod
    async def get_oauth_authorization_url(
        self,
        user_id: int,
        redirect_uri: str,
        state: Optional[str] = None,
    ) -> str:
        """Get OAuth authorization URL."""
        pass
    
    @abstractmethod
    async def exchange_code_for_token(
        self,
        code: str,
        redirect_uri: str,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        pass
    
    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        pass
    
    @abstractmethod
    async def get_free_busy(
        self,
        user: User,
        oauth_token: OAuthToken,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Tuple[datetime, datetime]]:
        """Get free/busy information for a user."""
        pass
    
    @abstractmethod
    async def create_event(
        self,
        user: User,
        oauth_token: OAuthToken,
        title: str,
        description: Optional[str],
        start_time: datetime,
        end_time: datetime,
        attendees: List[str],
    ) -> str:
        """Create a calendar event."""
        pass
    
    @abstractmethod
    async def update_event(
        self,
        user: User,
        oauth_token: OAuthToken,
        event_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        attendees: Optional[List[str]] = None,
    ) -> bool:
        """Update an existing calendar event."""
        pass
    
    @abstractmethod
    async def delete_event(
        self,
        user: User,
        oauth_token: OAuthToken,
        event_id: str,
    ) -> bool:
        """Delete a calendar event."""
        pass
    
    @abstractmethod
    async def get_event(
        self,
        user: User,
        oauth_token: OAuthToken,
        event_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get event details by ID."""
        pass
    
    @abstractmethod
    async def list_events(
        self,
        user: User,
        oauth_token: OAuthToken,
        start_time: datetime,
        end_time: datetime,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """List events in a time range."""
        pass
    
    @abstractmethod
    async def validate_token(self, oauth_token: OAuthToken) -> bool:
        """Validate if OAuth token is still valid."""
        pass
    
    @abstractmethod
    async def get_user_info(
        self,
        user: User,
        oauth_token: OAuthToken,
    ) -> Dict[str, Any]:
        """Get user information from the provider."""
        pass


class CalendarProviderError(Exception):
    """Base exception for calendar provider errors."""
    
    def __init__(self, message: str, provider: str, error_code: Optional[str] = None):
        """Initialize calendar provider error."""
        super().__init__(message)
        self.provider = provider
        self.error_code = error_code


class OAuthError(CalendarProviderError):
    """OAuth-related error."""
    pass


class TokenExpiredError(CalendarProviderError):
    """Token expired error."""
    pass


class RateLimitError(CalendarProviderError):
    """Rate limit exceeded error."""
    pass


class PermissionError(CalendarProviderError):
    """Permission denied error."""
    pass


class EventNotFoundError(CalendarProviderError):
    """Event not found error."""
    pass


