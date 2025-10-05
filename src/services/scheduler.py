"""Scheduler service for meeting lifecycle management."""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.user import User
from models.oauth import OAuthToken
from models.meeting import Meeting, MeetingParticipant, MeetingState, ParticipantRole
from models.vote import Vote, VoteType
from services.roster import RosterService
from providers.base import CalendarProvider
from providers.google import GoogleCalendarProvider
from utils.scheduling import (
    generate_time_slots,
    clip_to_working_hours,
    find_common_slots,
    paginate_slots,
    sort_slots_by_start_time,
    filter_slots_by_date_range,
)
from utils.timezone import utc_now
from utils.validation import validate_meeting_topic


class SchedulerService:
    """Service for managing meeting lifecycle and scheduling."""
    
    def __init__(self, db_session: AsyncSession):
        """Initialize scheduler service with database session."""
        self.db = db_session
        self.roster_service = RosterService(db_session)
        self.google_provider = GoogleCalendarProvider()
    
    async def create_meeting(
        self,
        organizer_id: int,
        chat_id: int,
        topic: str,
        duration_min: int,
        participant_telegram_ids: List[int],
        description: Optional[str] = None,
    ) -> Meeting:
        """Create a new meeting."""
        # Validate topic
        if not validate_meeting_topic(topic):
            raise ValueError("Invalid meeting topic")
        
        # Validate participants
        validation_result = await self.roster_service.validate_participants(
            participant_telegram_ids, chat_id
        )
        
        if not validation_result["all_valid"]:
            raise ValueError(f"Invalid participants: {validation_result['invalid_participants']}")
        
        # Create meeting
        meeting = Meeting(
            chat_id=chat_id,
            organizer_id=organizer_id,
            topic=topic,
            duration_min=duration_min,
            description=description,
            state=MeetingState.DRAFT,
        )
        
        self.db.add(meeting)
        await self.db.flush()  # Get the ID
        
        # Add participants
        for user in validation_result["valid_participants"]:
            participant = MeetingParticipant(
                meeting_id=meeting.id,
                user_id=user.id,
                role=ParticipantRole.REQUIRED,
            )
            self.db.add(participant)
        
        # Add organizer as participant
        organizer_participant = MeetingParticipant(
            meeting_id=meeting.id,
            user_id=organizer_id,
            role=ParticipantRole.REQUIRED,
        )
        self.db.add(organizer_participant)
        
        # Check OAuth status and set initial state
        await self._check_oauth_status(meeting)
        
        await self.db.commit()
        await self.db.refresh(meeting)
        
        return meeting
    
    async def _check_oauth_status(self, meeting: Meeting) -> None:
        """Check OAuth status for all participants and set meeting state."""
        # Get all participants
        stmt = (
            select(User)
            .join(MeetingParticipant, User.id == MeetingParticipant.user_id)
            .where(MeetingParticipant.meeting_id == meeting.id)
        )
        result = await self.db.execute(stmt)
        participants = result.scalars().all()
        
        # Check OAuth tokens for each participant
        missing_oauth = []
        for participant in participants:
            oauth_token = await self._get_oauth_token(participant.id, "google")
            if not oauth_token or not await self._validate_oauth_token(oauth_token):
                missing_oauth.append(participant)
        
        # Set meeting state based on OAuth status
        if missing_oauth:
            meeting.state = MeetingState.AWAITING_CONSENT
        else:
            meeting.state = MeetingState.RESOLVING
    
    async def _get_oauth_token(self, user_id: int, provider: str) -> Optional[OAuthToken]:
        """Get OAuth token for user and provider."""
        stmt = select(OAuthToken).where(
            and_(OAuthToken.user_id == user_id, OAuthToken.provider == provider)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _validate_oauth_token(self, oauth_token: OAuthToken) -> bool:
        """Validate OAuth token."""
        if not oauth_token.is_active:
            return False
        
        if oauth_token.is_expired:
            # Try to refresh token
            try:
                await self._refresh_oauth_token(oauth_token)
            except Exception:
                return False
        
        # Validate with provider
        return await self.google_provider.validate_token(oauth_token)
    
    async def _refresh_oauth_token(self, oauth_token: OAuthToken) -> None:
        """Refresh OAuth token."""
        if not oauth_token.refresh_token:
            raise ValueError("No refresh token available")
        
        try:
            token_data = await self.google_provider.refresh_access_token(
                oauth_token.refresh_token
            )
            
            # Update token
            oauth_token.access_token = token_data["access_token"]
            oauth_token.expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=token_data.get("expires_in", 3600)
            )
            oauth_token.updated_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            
        except Exception as e:
            # Mark token as inactive
            oauth_token.is_active = False
            await self.db.commit()
            raise e
    
    async def resolve_available_slots(
        self,
        meeting_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Tuple[datetime, datetime]]:
        """Resolve available time slots for a meeting."""
        # Get meeting
        meeting = await self._get_meeting_with_participants(meeting_id)
        if not meeting:
            raise ValueError("Meeting not found")
        
        if meeting.state != MeetingState.RESOLVING:
            raise ValueError(f"Meeting is not in resolving state: {meeting.state}")
        
        # Set default date range (next 10 business days)
        if not start_date:
            start_date = utc_now()
        if not end_date:
            end_date = start_date + timedelta(days=10)
        
        # Get all participants with valid OAuth tokens
        participants = []
        for participant in meeting.participants:
            oauth_token = await self._get_oauth_token(participant.user_id, "google")
            if oauth_token and await self._validate_oauth_token(oauth_token):
                participants.append((participant.user, oauth_token))
        
        if not participants:
            raise ValueError("No participants with valid OAuth tokens")
        
        # Get free/busy information for each participant
        all_participant_slots = []
        
        for user, oauth_token in participants:
            try:
                # Get busy times from Google Calendar
                busy_times = await self.google_provider.get_free_busy(
                    user, oauth_token, start_date, end_date
                )
                
                # Generate available slots (inverse of busy times)
                available_slots = self._generate_available_slots(
                    start_date, end_date, busy_times, meeting.duration_min
                )
                
                # Clip to working hours
                clipped_slots = clip_to_working_hours(
                    available_slots,
                    user.timezone,
                    user.working_hours_start,
                    user.working_hours_end,
                )
                
                all_participant_slots.append(clipped_slots)
                
            except Exception as e:
                # Log error and continue with other participants
                print(f"Error getting free/busy for user {user.id}: {e}")
                continue
        
        if not all_participant_slots:
            raise ValueError("Could not get free/busy information for any participant")
        
        # Find common slots across all participants
        common_slots = find_common_slots(all_participant_slots)
        
        # Sort by start time
        common_slots = sort_slots_by_start_time(common_slots)
        
        # Filter by date range
        common_slots = filter_slots_by_date_range(common_slots, start_date, end_date)
        
        return common_slots
    
    def _generate_available_slots(
        self,
        start_date: datetime,
        end_date: datetime,
        busy_times: List[Tuple[datetime, datetime]],
        duration_min: int,
    ) -> List[Tuple[datetime, datetime]]:
        """Generate available slots from busy times."""
        available_slots = []
        
        # Sort busy times by start time
        busy_times = sorted(busy_times, key=lambda x: x[0])
        
        current_time = start_date
        
        for busy_start, busy_end in busy_times:
            # Add available slot before busy time
            if current_time < busy_start:
                slot_end = min(busy_start, current_time + timedelta(minutes=duration_min))
                if slot_end - current_time >= timedelta(minutes=duration_min):
                    available_slots.append((current_time, slot_end))
            
            # Move current time to end of busy period
            current_time = max(current_time, busy_end)
        
        # Add final available slot if there's time left
        if current_time < end_date:
            slot_end = min(end_date, current_time + timedelta(minutes=duration_min))
            if slot_end - current_time >= timedelta(minutes=duration_min):
                available_slots.append((current_time, slot_end))
        
        return available_slots
    
    async def start_voting(
        self,
        meeting_id: int,
        slots: List[Tuple[datetime, datetime]],
    ) -> None:
        """Start voting phase for a meeting."""
        meeting = await self._get_meeting_with_participants(meeting_id)
        if not meeting:
            raise ValueError("Meeting not found")
        
        if meeting.state != MeetingState.RESOLVING:
            raise ValueError(f"Meeting is not in resolving state: {meeting.state}")
        
        # Update meeting state
        meeting.state = MeetingState.VOTING
        meeting.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
    
    async def cast_vote(
        self,
        meeting_id: int,
        user_id: int,
        slot_start: datetime,
        slot_end: datetime,
        vote_type: VoteType,
    ) -> Vote:
        """Cast a vote for a time slot."""
        # Check if user is a participant
        stmt = select(MeetingParticipant).where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        participant = result.scalar_one_or_none()
        
        if not participant:
            raise ValueError("User is not a participant in this meeting")
        
        # Check if vote already exists
        stmt = select(Vote).where(
            and_(
                Vote.meeting_id == meeting_id,
                Vote.user_id == user_id,
                Vote.slot_start_utc == slot_start,
            )
        )
        result = await self.db.execute(stmt)
        existing_vote = result.scalar_one_or_none()
        
        if existing_vote:
            # Update existing vote
            existing_vote.vote = vote_type
            existing_vote.voted_at = datetime.now(timezone.utc)
            await self.db.commit()
            return existing_vote
        
        # Create new vote
        vote = Vote(
            meeting_id=meeting_id,
            user_id=user_id,
            slot_start_utc=slot_start,
            slot_end_utc=slot_end,
            vote=vote_type,
            voted_at=datetime.now(timezone.utc),
        )
        
        self.db.add(vote)
        await self.db.commit()
        await self.db.refresh(vote)
        
        return vote
    
    async def get_voting_results(
        self,
        meeting_id: int,
        slots: List[Tuple[datetime, datetime]],
    ) -> List[Dict[str, Any]]:
        """Get voting results for time slots."""
        results = []
        
        for slot_start, slot_end in slots:
            # Get votes for this slot
            stmt = select(Vote).where(
                and_(
                    Vote.meeting_id == meeting_id,
                    Vote.slot_start_utc == slot_start,
                )
            )
            result = await self.db.execute(stmt)
            votes = result.scalars().all()
            
            # Count votes
            vote_counts = {
                VoteType.YES: 0,
                VoteType.NO: 0,
                VoteType.MAYBE: 0,
            }
            
            for vote in votes:
                vote_counts[vote.vote] += 1
            
            # Get total participants
            stmt = select(MeetingParticipant).where(
                MeetingParticipant.meeting_id == meeting_id
            )
            result = await self.db.execute(stmt)
            total_participants = len(result.scalars().all())
            
            results.append({
                "slot_start": slot_start,
                "slot_end": slot_end,
                "votes": vote_counts,
                "total_participants": total_participants,
                "participation_rate": len(votes) / total_participants if total_participants > 0 else 0,
            })
        
        return results
    
    async def confirm_meeting(
        self,
        meeting_id: int,
        chosen_start: datetime,
        chosen_end: datetime,
    ) -> str:
        """Confirm meeting and create calendar event."""
        meeting = await self._get_meeting_with_participants(meeting_id)
        if not meeting:
            raise ValueError("Meeting not found")
        
        if meeting.state != MeetingState.VOTING:
            raise ValueError(f"Meeting is not in voting state: {meeting.state}")
        
        # Get organizer
        organizer = await self.roster_service.get_user_by_id(meeting.organizer_id)
        if not organizer:
            raise ValueError("Organizer not found")
        
        # Get organizer's OAuth token
        oauth_token = await self._get_oauth_token(organizer.id, "google")
        if not oauth_token:
            raise ValueError("Organizer does not have OAuth token")
        
        # Validate OAuth token
        if not await self._validate_oauth_token(oauth_token):
            raise ValueError("Organizer's OAuth token is invalid")
        
        # Re-validate availability before creating event
        try:
            busy_times = await self.google_provider.get_free_busy(
                organizer, oauth_token, chosen_start, chosen_end
            )
            
            # Check if chosen slot is still available
            for busy_start, busy_end in busy_times:
                if busy_start <= chosen_start < busy_end or busy_start < chosen_end <= busy_end:
                    raise ValueError("Chosen time slot is no longer available")
        
        except Exception as e:
            raise ValueError(f"Could not validate availability: {e}")
        
        # Get participant emails
        participant_emails = []
        for participant in meeting.participants:
            # In a real implementation, you would get email from user profile
            # For now, we'll use a placeholder
            participant_emails.append(f"user_{participant.user_id}@example.com")
        
        # Create calendar event
        try:
            event_id = await self.google_provider.create_event(
                user=organizer,
                oauth_token=oauth_token,
                title=meeting.topic,
                description=meeting.description,
                start_time=chosen_start,
                end_time=chosen_end,
                attendees=participant_emails,
            )
            
            # Update meeting
            meeting.state = MeetingState.CONFIRMED
            meeting.chosen_start_utc = chosen_start
            meeting.chosen_end_utc = chosen_end
            meeting.calendar_event_id = event_id
            meeting.updated_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            
            return event_id
            
        except Exception as e:
            # Mark meeting as failed
            meeting.state = MeetingState.FAILED
            meeting.updated_at = datetime.now(timezone.utc)
            await self.db.commit()
            
            raise ValueError(f"Failed to create calendar event: {e}")
    
    async def cancel_meeting(self, meeting_id: int, reason: Optional[str] = None) -> bool:
        """Cancel a meeting."""
        meeting = await self._get_meeting_with_participants(meeting_id)
        if not meeting:
            return False
        
        # Update meeting state
        meeting.state = MeetingState.CANCELED
        meeting.updated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        return True
    
    async def _get_meeting_with_participants(self, meeting_id: int) -> Optional[Meeting]:
        """Get meeting with participants loaded."""
        stmt = (
            select(Meeting)
            .options(selectinload(Meeting.participants).selectinload(MeetingParticipant.user))
            .where(Meeting.id == meeting_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_meeting(self, meeting_id: int) -> Optional[Meeting]:
        """Get meeting by ID."""
        return await self._get_meeting_with_participants(meeting_id)
    
    async def get_user_meetings(
        self,
        user_id: int,
        state: Optional[MeetingState] = None,
        limit: int = 50,
    ) -> List[Meeting]:
        """Get meetings for a user."""
        stmt = (
            select(Meeting)
            .join(MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id)
            .where(MeetingParticipant.user_id == user_id)
        )
        
        if state:
            stmt = stmt.where(Meeting.state == state)
        
        stmt = stmt.order_by(Meeting.created_at.desc()).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_chat_meetings(
        self,
        chat_id: int,
        state: Optional[MeetingState] = None,
        limit: int = 50,
    ) -> List[Meeting]:
        """Get meetings for a chat."""
        stmt = select(Meeting).where(Meeting.chat_id == chat_id)
        
        if state:
            stmt = stmt.where(Meeting.state == state)
        
        stmt = stmt.order_by(Meeting.created_at.desc()).limit(limit)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()


