"""Meeting endpoints for meeting management."""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Body, Path, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session
from models.user import User
from models.meeting import Meeting, MeetingState
from models.vote import VoteType
from services.scheduler import SchedulerService
from services.roster import RosterService
from services.notification import NotificationService
from providers.telegram import TelegramProvider
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Create router
router = APIRouter(prefix="/meetings", tags=["meetings"])


# Pydantic models for request/response
class MeetingCreateRequest(BaseModel):
    """Request model for creating a meeting."""
    
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


class MeetingResolveRequest(BaseModel):
    """Request model for resolving meeting time slots."""
    
    start_date: Optional[datetime] = Field(None, description="Start date for slot search")
    end_date: Optional[datetime] = Field(None, description="End date for slot search")


class MeetingConfirmRequest(BaseModel):
    """Request model for confirming a meeting."""
    
    chosen_start: datetime = Field(..., description="Chosen meeting start time")
    chosen_end: datetime = Field(..., description="Chosen meeting end time")
    
    @validator("chosen_end")
    def validate_end_time(cls, v, values):
        """Validate end time is after start time."""
        if "chosen_start" in values and v <= values["chosen_start"]:
            raise ValueError("End time must be after start time")
        return v


class VoteRequest(BaseModel):
    """Request model for casting a vote."""
    
    user_telegram_id: int = Field(..., description="Voter's Telegram ID")
    slot_start: datetime = Field(..., description="Slot start time")
    slot_end: datetime = Field(..., description="Slot end time")
    vote: VoteType = Field(..., description="Vote type")


class MeetingResponse(BaseModel):
    """Response model for meeting data."""
    
    id: int
    topic: str
    duration_min: int
    description: Optional[str]
    state: str
    chosen_start_utc: Optional[datetime]
    chosen_end_utc: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    participant_count: int
    vote_count: int


class TimeSlotResponse(BaseModel):
    """Response model for time slot data."""
    
    start: datetime
    end: datetime
    duration_min: int


class VoteResponse(BaseModel):
    """Response model for vote data."""
    
    slot_start: datetime
    slot_end: datetime
    votes: Dict[str, int]
    total_participants: int
    participation_rate: float


@router.post("/", response_model=MeetingResponse)
async def create_meeting(
    request: MeetingCreateRequest,
    db: AsyncSession = Depends(get_session),
) -> MeetingResponse:
    """
    Create a new meeting.
    
    Args:
        request: Meeting creation request
        db: Database session
        
    Returns:
        Created meeting data
    """
    try:
        # Get organizer
        roster_service = RosterService(db)
        organizer = await roster_service.get_user_by_telegram_id(request.organizer_telegram_id)
        if not organizer:
            raise HTTPException(status_code=404, detail="Organizer not found")
        
        # Get or create chat
        chat = await roster_service.get_or_create_chat(
            telegram_chat_id=request.chat_telegram_id,
            title="Unknown Chat",  # This would be retrieved from Telegram API
            chat_type="group",
        )
        
        # Validate participants
        validation_result = await roster_service.validate_participants(
            request.participant_telegram_ids, chat.id
        )
        
        if not validation_result["all_valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid participants: {validation_result['invalid_participants']}"
            )
        
        # Create meeting
        scheduler_service = SchedulerService(db)
        meeting = await scheduler_service.create_meeting(
            organizer_id=organizer.id,
            chat_id=chat.id,
            topic=request.topic,
            duration_min=request.duration_min,
            participant_telegram_ids=request.participant_telegram_ids,
            description=request.description,
        )
        
        # Send notifications
        telegram_provider = TelegramProvider(settings.telegram_bot_token)
        notification_service = NotificationService(db, telegram_provider)
        
        participants = validation_result["valid_participants"]
        await notification_service.send_meeting_created_notification(
            meeting=meeting,
            organizer=organizer,
            participants=participants,
        )
        
        logger.info(f"Meeting created: {meeting.id} by user {organizer.telegram_id}")
        
        return MeetingResponse(
            id=meeting.id,
            topic=meeting.topic,
            duration_min=meeting.duration_min,
            description=meeting.description,
            state=meeting.state.value,
            chosen_start_utc=meeting.chosen_start_utc,
            chosen_end_utc=meeting.chosen_end_utc,
            created_at=meeting.created_at,
            updated_at=meeting.updated_at,
            participant_count=len(meeting.participants),
            vote_count=len(meeting.votes),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating meeting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create meeting")


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: int = Path(..., description="Meeting ID"),
    db: AsyncSession = Depends(get_session),
) -> MeetingResponse:
    """
    Get meeting by ID.
    
    Args:
        meeting_id: Meeting ID
        db: Database session
        
    Returns:
        Meeting data
    """
    try:
        scheduler_service = SchedulerService(db)
        meeting = await scheduler_service.get_meeting(meeting_id)
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        return MeetingResponse(
            id=meeting.id,
            topic=meeting.topic,
            duration_min=meeting.duration_min,
            description=meeting.description,
            state=meeting.state.value,
            chosen_start_utc=meeting.chosen_start_utc,
            chosen_end_utc=meeting.chosen_end_utc,
            created_at=meeting.created_at,
            updated_at=meeting.updated_at,
            participant_count=len(meeting.participants),
            vote_count=len(meeting.votes),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting meeting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get meeting")


@router.post("/{meeting_id}/resolve", response_model=List[TimeSlotResponse])
async def resolve_meeting_slots(
    meeting_id: int = Path(..., description="Meeting ID"),
    request: MeetingResolveRequest = Body(default_factory=MeetingResolveRequest),
    db: AsyncSession = Depends(get_session),
) -> List[TimeSlotResponse]:
    """
    Resolve available time slots for a meeting.
    
    Args:
        meeting_id: Meeting ID
        request: Resolve request with optional date range
        db: Database session
        
    Returns:
        List of available time slots
    """
    try:
        scheduler_service = SchedulerService(db)
        meeting = await scheduler_service.get_meeting(meeting_id)
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        if meeting.state != MeetingState.RESOLVING:
            raise HTTPException(
                status_code=400,
                detail=f"Meeting is not in resolving state: {meeting.state.value}"
            )
        
        # Resolve available slots
        slots = await scheduler_service.resolve_available_slots(
            meeting_id=meeting_id,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        
        # Start voting if slots found
        if slots:
            await scheduler_service.start_voting(meeting_id, slots)
            
            # Send voting notification
            telegram_provider = TelegramProvider(settings.telegram_bot_token)
            notification_service = NotificationService(db, telegram_provider)
            
            organizer = await scheduler_service.roster_service.get_user_by_id(meeting.organizer_id)
            participants = [p.user for p in meeting.participants]
            
            await notification_service.send_voting_notification(
                meeting=meeting,
                slots=slots,
                organizer=organizer,
            )
        
        return [
            TimeSlotResponse(
                start=slot_start,
                end=slot_end,
                duration_min=meeting.duration_min,
            )
            for slot_start, slot_end in slots
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving meeting slots: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to resolve meeting slots")


@router.post("/{meeting_id}/confirm", response_model=Dict[str, Any])
async def confirm_meeting(
    meeting_id: int = Path(..., description="Meeting ID"),
    request: MeetingConfirmRequest = Body(...),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Confirm a meeting with chosen time slot.
    
    Args:
        meeting_id: Meeting ID
        request: Confirmation request with chosen time
        db: Database session
        
    Returns:
        Confirmation result with calendar event ID
    """
    try:
        scheduler_service = SchedulerService(db)
        meeting = await scheduler_service.get_meeting(meeting_id)
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        if meeting.state != MeetingState.VOTING:
            raise HTTPException(
                status_code=400,
                detail=f"Meeting is not in voting state: {meeting.state.value}"
            )
        
        # Confirm meeting
        event_id = await scheduler_service.confirm_meeting(
            meeting_id=meeting_id,
            chosen_start=request.chosen_start,
            chosen_end=request.chosen_end,
        )
        
        # Send confirmation notifications
        telegram_provider = TelegramProvider(settings.telegram_bot_token)
        notification_service = NotificationService(db, telegram_provider)
        
        organizer = await scheduler_service.roster_service.get_user_by_id(meeting.organizer_id)
        participants = [p.user for p in meeting.participants]
        
        await notification_service.send_meeting_confirmed_notification(
            meeting=meeting,
            organizer=organizer,
            participants=participants,
        )
        
        logger.info(f"Meeting confirmed: {meeting_id}, event_id: {event_id}")
        
        return {
            "success": True,
            "meeting_id": meeting_id,
            "calendar_event_id": event_id,
            "chosen_start": request.chosen_start.isoformat(),
            "chosen_end": request.chosen_end.isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming meeting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to confirm meeting")


@router.post("/{meeting_id}/vote", response_model=Dict[str, Any])
async def cast_vote(
    meeting_id: int = Path(..., description="Meeting ID"),
    request: VoteRequest = Body(...),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Cast a vote for a time slot.
    
    Args:
        meeting_id: Meeting ID
        request: Vote request
        db: Database session
        
    Returns:
        Vote result
    """
    try:
        scheduler_service = SchedulerService(db)
        meeting = await scheduler_service.get_meeting(meeting_id)
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        if meeting.state != MeetingState.VOTING:
            raise HTTPException(
                status_code=400,
                detail=f"Meeting is not in voting state: {meeting.state.value}"
            )
        
        # Get user
        roster_service = RosterService(db)
        user = await roster_service.get_user_by_telegram_id(request.user_telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Cast vote
        vote = await scheduler_service.cast_vote(
            meeting_id=meeting_id,
            user_id=user.id,
            slot_start=request.slot_start,
            slot_end=request.slot_end,
            vote=request.vote,
        )
        
        # Send vote notification
        telegram_provider = TelegramProvider(settings.telegram_bot_token)
        notification_service = NotificationService(db, telegram_provider)
        
        await notification_service.send_vote_received_notification(
            meeting=meeting,
            voter=user,
            slot_start=request.slot_start,
            slot_end=request.slot_end,
            vote_type=request.vote,
        )
        
        logger.info(f"Vote cast: {meeting_id} by user {user.telegram_id}")
        
        return {
            "success": True,
            "vote_id": vote.id,
            "meeting_id": meeting_id,
            "user_id": user.id,
            "vote": request.vote.value,
            "voted_at": vote.voted_at.isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error casting vote: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to cast vote")


@router.get("/{meeting_id}/votes", response_model=List[VoteResponse])
async def get_voting_results(
    meeting_id: int = Path(..., description="Meeting ID"),
    db: AsyncSession = Depends(get_session),
) -> List[VoteResponse]:
    """
    Get voting results for a meeting.
    
    Args:
        meeting_id: Meeting ID
        db: Database session
        
    Returns:
        List of voting results for each time slot
    """
    try:
        scheduler_service = SchedulerService(db)
        meeting = await scheduler_service.get_meeting(meeting_id)
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        if meeting.state != MeetingState.VOTING:
            raise HTTPException(
                status_code=400,
                detail=f"Meeting is not in voting state: {meeting.state.value}"
            )
        
        # Get voting results (this would need to be implemented in the scheduler service)
        # For now, return empty list
        results = []
        
        return [
            VoteResponse(
                slot_start=result["slot_start"],
                slot_end=result["slot_end"],
                votes=result["votes"],
                total_participants=result["total_participants"],
                participation_rate=result["participation_rate"],
            )
            for result in results
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voting results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get voting results")


@router.delete("/{meeting_id}")
async def cancel_meeting(
    meeting_id: int = Path(..., description="Meeting ID"),
    reason: Optional[str] = Query(None, description="Cancellation reason"),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Cancel a meeting.
    
    Args:
        meeting_id: Meeting ID
        reason: Optional cancellation reason
        db: Database session
        
    Returns:
        Cancellation result
    """
    try:
        scheduler_service = SchedulerService(db)
        meeting = await scheduler_service.get_meeting(meeting_id)
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        if meeting.state in [MeetingState.CONFIRMED, MeetingState.CANCELED, MeetingState.FAILED]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel meeting in state: {meeting.state.value}"
            )
        
        # Cancel meeting
        success = await scheduler_service.cancel_meeting(meeting_id, reason)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to cancel meeting")
        
        # Send cancellation notifications
        telegram_provider = TelegramProvider(settings.telegram_bot_token)
        notification_service = NotificationService(db, telegram_provider)
        
        organizer = await scheduler_service.roster_service.get_user_by_id(meeting.organizer_id)
        participants = [p.user for p in meeting.participants]
        
        await notification_service.send_meeting_canceled_notification(
            meeting=meeting,
            organizer=organizer,
            participants=participants,
            reason=reason,
        )
        
        logger.info(f"Meeting canceled: {meeting_id}, reason: {reason}")
        
        return {
            "success": True,
            "meeting_id": meeting_id,
            "reason": reason,
            "canceled_at": datetime.now(timezone.utc).isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling meeting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to cancel meeting")


@router.get("/user/{telegram_id}", response_model=List[MeetingResponse])
async def get_user_meetings(
    telegram_id: int = Path(..., description="User's Telegram ID"),
    state: Optional[str] = Query(None, description="Filter by meeting state"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of meetings to return"),
    db: AsyncSession = Depends(get_session),
) -> List[MeetingResponse]:
    """
    Get meetings for a user.
    
    Args:
        telegram_id: User's Telegram ID
        state: Optional state filter
        limit: Maximum number of meetings to return
        db: Database session
        
    Returns:
        List of user's meetings
    """
    try:
        # Get user
        roster_service = RosterService(db)
        user = await roster_service.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get meetings
        scheduler_service = SchedulerService(db)
        
        # Convert state string to enum if provided
        meeting_state = None
        if state:
            try:
                meeting_state = MeetingState(state)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid state: {state}")
        
        meetings = await scheduler_service.get_user_meetings(
            user_id=user.id,
            state=meeting_state,
            limit=limit,
        )
        
        return [
            MeetingResponse(
                id=meeting.id,
                topic=meeting.topic,
                duration_min=meeting.duration_min,
                description=meeting.description,
                state=meeting.state.value,
                chosen_start_utc=meeting.chosen_start_utc,
                chosen_end_utc=meeting.chosen_end_utc,
                created_at=meeting.created_at,
                updated_at=meeting.updated_at,
                participant_count=len(meeting.participants),
                vote_count=len(meeting.votes),
            )
            for meeting in meetings
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user meetings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get user meetings")
