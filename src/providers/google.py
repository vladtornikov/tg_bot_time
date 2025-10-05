"""Google Calendar provider implementation."""
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlencode

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.settings import get_settings
from models.user import User
from models.oauth import OAuthToken
from providers.base import (
    CalendarProvider,
    CalendarProviderError,
    OAuthError,
    TokenExpiredError,
    RateLimitError,
    PermissionError,
    EventNotFoundError,
)
from utils.encryption import encryption_service

settings = get_settings()


class GoogleCalendarProvider(CalendarProvider):
    """Google Calendar provider implementation."""
    
    def __init__(self):
        """Initialize Google Calendar provider."""
        super().__init__("google")
        
        # OAuth 2.0 configuration
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri
        
        # OAuth scopes
        self.scopes = [
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ]
        
        # API endpoints
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    async def get_oauth_authorization_url(
        self,
        user_id: int,
        redirect_uri: str,
        state: Optional[str] = None,
    ) -> str:
        """Get OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.scopes),
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
        }
        
        if state:
            params["state"] = state
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(
        self,
        code: str,
        redirect_uri: str,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            }
            
            try:
                response = await client.post(self.token_url, data=data)
                response.raise_for_status()
                token_data = response.json()
                
                return {
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_in": token_data.get("expires_in"),
                    "token_type": token_data.get("token_type", "Bearer"),
                    "scope": token_data.get("scope"),
                }
                
            except httpx.HTTPError as e:
                raise OAuthError(f"Failed to exchange code for token: {e}", self.provider_name)
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
            
            try:
                response = await client.post(self.token_url, data=data)
                response.raise_for_status()
                token_data = response.json()
                
                return {
                    "access_token": token_data["access_token"],
                    "expires_in": token_data.get("expires_in"),
                    "token_type": token_data.get("token_type", "Bearer"),
                    "scope": token_data.get("scope"),
                }
                
            except httpx.HTTPError as e:
                raise TokenExpiredError(f"Failed to refresh token: {e}", self.provider_name)
    
    async def get_free_busy(
        self,
        user: User,
        oauth_token: OAuthToken,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Tuple[datetime, datetime]]:
        """Get free/busy information for a user."""
        try:
            # Decrypt access token
            access_token = encryption_service.decrypt(oauth_token.access_token)
            
            # Create credentials
            credentials = Credentials(
                token=access_token,
                refresh_token=encryption_service.decrypt(oauth_token.refresh_token) if oauth_token.refresh_token else None,
                token_uri=self.token_url,
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes,
            )
            
            # Build service
            service = build("calendar", "v3", credentials=credentials)
            
            # Query free/busy
            freebusy_query = {
                "timeMin": start_time.isoformat() + "Z",
                "timeMax": end_time.isoformat() + "Z",
                "items": [{"id": user.telegram_id}],  # Use user's primary calendar
            }
            
            freebusy_result = service.freebusy().query(body=freebusy_query).execute()
            
            # Parse busy times
            busy_times = []
            calendars = freebusy_result.get("calendars", {})
            
            for calendar_id, calendar_data in calendars.items():
                busy_periods = calendar_data.get("busy", [])
                
                for period in busy_periods:
                    start = datetime.fromisoformat(period["start"].replace("Z", "+00:00"))
                    end = datetime.fromisoformat(period["end"].replace("Z", "+00:00"))
                    busy_times.append((start, end))
            
            return busy_times
            
        except HttpError as e:
            if e.resp.status == 401:
                raise TokenExpiredError("Token expired or invalid", self.provider_name)
            elif e.resp.status == 403:
                raise PermissionError("Insufficient permissions", self.provider_name)
            elif e.resp.status == 429:
                raise RateLimitError("Rate limit exceeded", self.provider_name)
            else:
                raise CalendarProviderError(f"Google API error: {e}", self.provider_name)
        except Exception as e:
            raise CalendarProviderError(f"Unexpected error: {e}", self.provider_name)
    
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
        try:
            # Decrypt access token
            access_token = encryption_service.decrypt(oauth_token.access_token)
            
            # Create credentials
            credentials = Credentials(
                token=access_token,
                refresh_token=encryption_service.decrypt(oauth_token.refresh_token) if oauth_token.refresh_token else None,
                token_uri=self.token_url,
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes,
            )
            
            # Build service
            service = build("calendar", "v3", credentials=credentials)
            
            # Create event
            event = {
                "summary": title,
                "description": description,
                "start": {
                    "dateTime": start_time.isoformat(),
                    "timeZone": "UTC",
                },
                "end": {
                    "dateTime": end_time.isoformat(),
                    "timeZone": "UTC",
                },
                "attendees": [{"email": email} for email in attendees],
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 10},
                        {"method": "email", "minutes": 30},
                    ],
                },
            }
            
            created_event = service.events().insert(
                calendarId="primary",
                body=event,
                sendUpdates="all",
            ).execute()
            
            return created_event["id"]
            
        except HttpError as e:
            if e.resp.status == 401:
                raise TokenExpiredError("Token expired or invalid", self.provider_name)
            elif e.resp.status == 403:
                raise PermissionError("Insufficient permissions", self.provider_name)
            elif e.resp.status == 429:
                raise RateLimitError("Rate limit exceeded", self.provider_name)
            else:
                raise CalendarProviderError(f"Google API error: {e}", self.provider_name)
        except Exception as e:
            raise CalendarProviderError(f"Unexpected error: {e}", self.provider_name)
    
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
        try:
            # Decrypt access token
            access_token = encryption_service.decrypt(oauth_token.access_token)
            
            # Create credentials
            credentials = Credentials(
                token=access_token,
                refresh_token=encryption_service.decrypt(oauth_token.refresh_token) if oauth_token.refresh_token else None,
                token_uri=self.token_url,
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes,
            )
            
            # Build service
            service = build("calendar", "v3", credentials=credentials)
            
            # Get existing event
            existing_event = service.events().get(
                calendarId="primary",
                eventId=event_id,
            ).execute()
            
            # Update fields
            if title is not None:
                existing_event["summary"] = title
            if description is not None:
                existing_event["description"] = description
            if start_time is not None:
                existing_event["start"] = {
                    "dateTime": start_time.isoformat(),
                    "timeZone": "UTC",
                }
            if end_time is not None:
                existing_event["end"] = {
                    "dateTime": end_time.isoformat(),
                    "timeZone": "UTC",
                }
            if attendees is not None:
                existing_event["attendees"] = [{"email": email} for email in attendees]
            
            # Update event
            service.events().update(
                calendarId="primary",
                eventId=event_id,
                body=existing_event,
                sendUpdates="all",
            ).execute()
            
            return True
            
        except HttpError as e:
            if e.resp.status == 401:
                raise TokenExpiredError("Token expired or invalid", self.provider_name)
            elif e.resp.status == 403:
                raise PermissionError("Insufficient permissions", self.provider_name)
            elif e.resp.status == 404:
                raise EventNotFoundError("Event not found", self.provider_name)
            elif e.resp.status == 429:
                raise RateLimitError("Rate limit exceeded", self.provider_name)
            else:
                raise CalendarProviderError(f"Google API error: {e}", self.provider_name)
        except Exception as e:
            raise CalendarProviderError(f"Unexpected error: {e}", self.provider_name)
    
    async def delete_event(
        self,
        user: User,
        oauth_token: OAuthToken,
        event_id: str,
    ) -> bool:
        """Delete a calendar event."""
        try:
            # Decrypt access token
            access_token = encryption_service.decrypt(oauth_token.access_token)
            
            # Create credentials
            credentials = Credentials(
                token=access_token,
                refresh_token=encryption_service.decrypt(oauth_token.refresh_token) if oauth_token.refresh_token else None,
                token_uri=self.token_url,
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes,
            )
            
            # Build service
            service = build("calendar", "v3", credentials=credentials)
            
            # Delete event
            service.events().delete(
                calendarId="primary",
                eventId=event_id,
                sendUpdates="all",
            ).execute()
            
            return True
            
        except HttpError as e:
            if e.resp.status == 401:
                raise TokenExpiredError("Token expired or invalid", self.provider_name)
            elif e.resp.status == 403:
                raise PermissionError("Insufficient permissions", self.provider_name)
            elif e.resp.status == 404:
                raise EventNotFoundError("Event not found", self.provider_name)
            elif e.resp.status == 429:
                raise RateLimitError("Rate limit exceeded", self.provider_name)
            else:
                raise CalendarProviderError(f"Google API error: {e}", self.provider_name)
        except Exception as e:
            raise CalendarProviderError(f"Unexpected error: {e}", self.provider_name)
    
    async def get_event(
        self,
        user: User,
        oauth_token: OAuthToken,
        event_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get event details by ID."""
        try:
            # Decrypt access token
            access_token = encryption_service.decrypt(oauth_token.access_token)
            
            # Create credentials
            credentials = Credentials(
                token=access_token,
                refresh_token=encryption_service.decrypt(oauth_token.refresh_token) if oauth_token.refresh_token else None,
                token_uri=self.token_url,
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes,
            )
            
            # Build service
            service = build("calendar", "v3", credentials=credentials)
            
            # Get event
            event = service.events().get(
                calendarId="primary",
                eventId=event_id,
            ).execute()
            
            return event
            
        except HttpError as e:
            if e.resp.status == 401:
                raise TokenExpiredError("Token expired or invalid", self.provider_name)
            elif e.resp.status == 403:
                raise PermissionError("Insufficient permissions", self.provider_name)
            elif e.resp.status == 404:
                return None
            elif e.resp.status == 429:
                raise RateLimitError("Rate limit exceeded", self.provider_name)
            else:
                raise CalendarProviderError(f"Google API error: {e}", self.provider_name)
        except Exception as e:
            raise CalendarProviderError(f"Unexpected error: {e}", self.provider_name)
    
    async def list_events(
        self,
        user: User,
        oauth_token: OAuthToken,
        start_time: datetime,
        end_time: datetime,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """List events in a time range."""
        try:
            # Decrypt access token
            access_token = encryption_service.decrypt(oauth_token.access_token)
            
            # Create credentials
            credentials = Credentials(
                token=access_token,
                refresh_token=encryption_service.decrypt(oauth_token.refresh_token) if oauth_token.refresh_token else None,
                token_uri=self.token_url,
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes,
            )
            
            # Build service
            service = build("calendar", "v3", credentials=credentials)
            
            # List events
            events_result = service.events().list(
                calendarId="primary",
                timeMin=start_time.isoformat() + "Z",
                timeMax=end_time.isoformat() + "Z",
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            
            return events_result.get("items", [])
            
        except HttpError as e:
            if e.resp.status == 401:
                raise TokenExpiredError("Token expired or invalid", self.provider_name)
            elif e.resp.status == 403:
                raise PermissionError("Insufficient permissions", self.provider_name)
            elif e.resp.status == 429:
                raise RateLimitError("Rate limit exceeded", self.provider_name)
            else:
                raise CalendarProviderError(f"Google API error: {e}", self.provider_name)
        except Exception as e:
            raise CalendarProviderError(f"Unexpected error: {e}", self.provider_name)
    
    async def validate_token(self, oauth_token: OAuthToken) -> bool:
        """Validate if OAuth token is still valid."""
        try:
            # Decrypt access token
            access_token = encryption_service.decrypt(oauth_token.access_token)
            
            # Create credentials
            credentials = Credentials(
                token=access_token,
                refresh_token=encryption_service.decrypt(oauth_token.refresh_token) if oauth_token.refresh_token else None,
                token_uri=self.token_url,
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.scopes,
            )
            
            # Try to make a simple API call
            service = build("calendar", "v3", credentials=credentials)
            service.calendarList().list(maxResults=1).execute()
            
            return True
            
        except HttpError as e:
            if e.resp.status == 401:
                return False
            else:
                return False
        except Exception:
            return False
    
    async def get_user_info(
        self,
        user: User,
        oauth_token: OAuthToken,
    ) -> Dict[str, Any]:
        """Get user information from the provider."""
        try:
            # Decrypt access token
            access_token = encryption_service.decrypt(oauth_token.access_token)
            
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                response = await client.get(self.userinfo_url, headers=headers)
                response.raise_for_status()
                
                return response.json()
                
        except httpx.HTTPError as e:
            raise CalendarProviderError(f"Failed to get user info: {e}", self.provider_name)


