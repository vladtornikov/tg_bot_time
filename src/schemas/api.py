"""Pydantic schemas for API request/response models."""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from enum import Enum

from pydantic import BaseModel, Field, validator


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Error timestamp")


class SuccessResponse(BaseModel):
    """Standard success response schema."""
    
    success: bool = Field(True, description="Success indicator")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Response timestamp")


class HealthResponse(BaseModel):
    """Health check response schema."""
    
    status: str = Field(..., description="Service status")
    timestamp: float = Field(..., description="Unix timestamp")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Environment name")
    database: Optional[str] = Field(None, description="Database status")
    redis: Optional[str] = Field(None, description="Redis status")


class OAuthStartRequest(BaseModel):
    """OAuth start request schema."""
    
    user_id: int = Field(..., description="Telegram user ID")
    redirect_uri: Optional[str] = Field(None, description="Redirect URI after OAuth")


class OAuthStartResponse(BaseModel):
    """OAuth start response schema."""
    
    authorization_url: str = Field(..., description="OAuth authorization URL")
    state: str = Field(..., description="OAuth state parameter")
    expires_in: int = Field(..., description="State expiration time in seconds")


class OAuthStatusResponse(BaseModel):
    """OAuth status response schema."""
    
    connected: bool = Field(..., description="Whether OAuth is connected")
    status: str = Field(..., description="OAuth status")
    message: str = Field(..., description="Status message")
    expires_at: Optional[datetime] = Field(None, description="Token expiration time")


class OAuthRefreshResponse(BaseModel):
    """OAuth refresh response schema."""
    
    success: bool = Field(..., description="Refresh success indicator")
    expires_at: Optional[datetime] = Field(None, description="New token expiration time")


class MeetingStateEnum(str, Enum):
    """Meeting state enumeration."""
    
    DRAFT = "draft"
    AWAITING_CONSENT = "awaiting_consent"
    RESOLVING = "resolving"
    VOTING = "voting"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELED = "canceled"


class VoteTypeEnum(str, Enum):
    """Vote type enumeration."""
    
    YES = "yes"
    NO = "no"
    MAYBE = "maybe"


class MeetingCreateRequest(BaseModel):
    """Meeting creation request schema."""
    
    organizer_telegram_id: int = Field(..., description="Organizer's Telegram ID")
    chat_telegram_id: int = Field(..., description="Chat's Telegram ID")
    topic: str = Field(..., min_length=1, max_length=500, description="Meeting topic")
    duration_min: int = Field(..., ge=15, le=480, description="Meeting duration in minutes")
    participant_telegram_ids: List[int] = Field(..., min_items=1, max_items=30, description="Participant Telegram IDs")
    description: Optional[str] = Field(None, max_length=2000, description="Meeting description")
    
    @validator("topic")
    def validate_topic(cls, v):
        """Validate meeting topic."""
        if not v.strip():
            raise ValueError("Topic cannot be empty")
        return v.strip()
    
    @validator("participant_telegram_ids")
    def validate_participants(cls, v):
        """Validate participants list."""
        if len(set(v)) != len(v):
            raise ValueError("Duplicate participants not allowed")
        return v


class MeetingResponse(BaseModel):
    """Meeting response schema."""
    
    id: int = Field(..., description="Meeting ID")
    topic: str = Field(..., description="Meeting topic")
    duration_min: int = Field(..., description="Meeting duration in minutes")
    description: Optional[str] = Field(None, description="Meeting description")
    state: MeetingStateEnum = Field(..., description="Meeting state")
    chosen_start_utc: Optional[datetime] = Field(None, description="Chosen start time")
    chosen_end_utc: Optional[datetime] = Field(None, description="Chosen end time")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    participant_count: int = Field(..., description="Number of participants")
    vote_count: int = Field(..., description="Number of votes")


class MeetingResolveRequest(BaseModel):
    """Meeting resolve request schema."""
    
    start_date: Optional[datetime] = Field(None, description="Start date for slot search")
    end_date: Optional[datetime] = Field(None, description="End date for slot search")


class TimeSlotResponse(BaseModel):
    """Time slot response schema."""
    
    start: datetime = Field(..., description="Slot start time")
    end: datetime = Field(..., description="Slot end time")
    duration_min: int = Field(..., description="Slot duration in minutes")


class MeetingConfirmRequest(BaseModel):
    """Meeting confirmation request schema."""
    
    chosen_start: datetime = Field(..., description="Chosen meeting start time")
    chosen_end: datetime = Field(..., description="Chosen meeting end time")
    
    @validator("chosen_end")
    def validate_end_time(cls, v, values):
        """Validate end time is after start time."""
        if "chosen_start" in values and v <= values["chosen_start"]:
            raise ValueError("End time must be after start time")
        return v


class MeetingConfirmResponse(BaseModel):
    """Meeting confirmation response schema."""
    
    success: bool = Field(..., description="Confirmation success indicator")
    meeting_id: int = Field(..., description="Meeting ID")
    calendar_event_id: str = Field(..., description="Calendar event ID")
    chosen_start: datetime = Field(..., description="Chosen start time")
    chosen_end: datetime = Field(..., description="Chosen end time")


class VoteRequest(BaseModel):
    """Vote request schema."""
    
    user_telegram_id: int = Field(..., description="Voter's Telegram ID")
    slot_start: datetime = Field(..., description="Slot start time")
    slot_end: datetime = Field(..., description="Slot end time")
    vote: VoteTypeEnum = Field(..., description="Vote type")


class VoteResponse(BaseModel):
    """Vote response schema."""
    
    success: bool = Field(..., description="Vote success indicator")
    vote_id: int = Field(..., description="Vote ID")
    meeting_id: int = Field(..., description="Meeting ID")
    user_id: int = Field(..., description="User ID")
    vote: VoteTypeEnum = Field(..., description="Vote type")
    voted_at: datetime = Field(..., description="Vote timestamp")


class VotingResultsResponse(BaseModel):
    """Voting results response schema."""
    
    slot_start: datetime = Field(..., description="Slot start time")
    slot_end: datetime = Field(..., description="Slot end time")
    votes: Dict[str, int] = Field(..., description="Vote counts by type")
    total_participants: int = Field(..., description="Total number of participants")
    participation_rate: float = Field(..., description="Participation rate")


class MeetingCancelRequest(BaseModel):
    """Meeting cancellation request schema."""
    
    reason: Optional[str] = Field(None, max_length=500, description="Cancellation reason")


class MeetingCancelResponse(BaseModel):
    """Meeting cancellation response schema."""
    
    success: bool = Field(..., description="Cancellation success indicator")
    meeting_id: int = Field(..., description="Meeting ID")
    reason: Optional[str] = Field(None, description="Cancellation reason")
    canceled_at: datetime = Field(..., description="Cancellation timestamp")


class UserMeetingsRequest(BaseModel):
    """User meetings request schema."""
    
    state: Optional[MeetingStateEnum] = Field(None, description="Filter by meeting state")
    limit: int = Field(50, ge=1, le=100, description="Maximum number of meetings to return")


class PaginationResponse(BaseModel):
    """Pagination response schema."""
    
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total: int = Field(..., description="Total number of items")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class PaginatedMeetingResponse(BaseModel):
    """Paginated meeting response schema."""
    
    meetings: List[MeetingResponse] = Field(..., description="List of meetings")
    pagination: PaginationResponse = Field(..., description="Pagination information")


class APIStatsResponse(BaseModel):
    """API statistics response schema."""
    
    total_requests: int = Field(..., description="Total number of requests")
    successful_requests: int = Field(..., description="Number of successful requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    average_response_time: float = Field(..., description="Average response time in seconds")
    uptime: float = Field(..., description="Service uptime in seconds")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Environment name")


class WebhookRequest(BaseModel):
    """Webhook request schema."""
    
    url: str = Field(..., description="Webhook URL")
    secret_token: Optional[str] = Field(None, description="Webhook secret token")


class WebhookResponse(BaseModel):
    """Webhook response schema."""
    
    success: bool = Field(..., description="Webhook setup success indicator")
    url: str = Field(..., description="Webhook URL")
    message: str = Field(..., description="Response message")
