"""Notification service for Telegram messaging."""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from models.meeting import Meeting, MeetingState
from models.vote import Vote, VoteType
from providers.telegram import TelegramProvider, create_vote_keyboard, create_participant_keyboard
from utils.timezone import format_datetime


class NotificationService:
    """Service for sending notifications via Telegram."""
    
    def __init__(self, db_session: AsyncSession, telegram_provider: TelegramProvider):
        """Initialize notification service."""
        self.db = db_session
        self.telegram = telegram_provider
    
    async def send_meeting_created_notification(
        self,
        meeting: Meeting,
        organizer: User,
        participants: List[User],
    ) -> None:
        """Send notification when a meeting is created."""
        if meeting.state == MeetingState.AWAITING_CONSENT:
            await self._send_oauth_consent_notifications(meeting, participants)
        elif meeting.state == MeetingState.RESOLVING:
            await self._send_meeting_created_message(meeting, organizer)
    
    async def _send_oauth_consent_notifications(
        self,
        meeting: Meeting,
        participants: List[User],
    ) -> None:
        """Send OAuth consent notifications to participants."""
        for participant in participants:
            try:
                message = self._get_oauth_consent_message(meeting, participant)
                await self.telegram.send_dm(
                    user_id=participant.telegram_id,
                    text=message,
                )
            except Exception as e:
                print(f"Failed to send OAuth consent to user {participant.id}: {e}")
    
    async def _send_meeting_created_message(
        self,
        meeting: Meeting,
        organizer: User,
    ) -> None:
        """Send meeting created message to chat."""
        try:
            message = self._get_meeting_created_message(meeting, organizer)
            await self.telegram.send_message(
                chat_id=meeting.chat_id,
                text=message,
            )
        except Exception as e:
            print(f"Failed to send meeting created message: {e}")
    
    async def send_voting_notification(
        self,
        meeting: Meeting,
        slots: List[tuple],
        organizer: User,
    ) -> None:
        """Send voting notification with time slots."""
        try:
            message = self._get_voting_message(meeting, organizer, slots)
            keyboard = create_vote_keyboard(slots, meeting.id)
            
            sent_message = await self.telegram.send_message(
                chat_id=meeting.chat_id,
                text=message,
                reply_markup=keyboard,
            )
            
            # Update meeting with message ID
            meeting.message_id = sent_message.message_id
            await self.db.commit()
            
        except Exception as e:
            print(f"Failed to send voting notification: {e}")
    
    async def send_vote_received_notification(
        self,
        meeting: Meeting,
        voter: User,
        slot_start: datetime,
        slot_end: datetime,
        vote_type: VoteType,
    ) -> None:
        """Send notification when a vote is received."""
        try:
            message = self._get_vote_received_message(
                meeting, voter, slot_start, slot_end, vote_type
            )
            
            # Send to chat if it's a yes vote
            if vote_type == VoteType.YES:
                await self.telegram.send_message(
                    chat_id=meeting.chat_id,
                    text=message,
                )
            
        except Exception as e:
            print(f"Failed to send vote received notification: {e}")
    
    async def send_meeting_confirmed_notification(
        self,
        meeting: Meeting,
        organizer: User,
        participants: List[User],
    ) -> None:
        """Send notification when meeting is confirmed."""
        try:
            # Update the voting message
            if meeting.message_id:
                message = self._get_meeting_confirmed_message(meeting, organizer)
                await self.telegram.edit_message_text(
                    chat_id=meeting.chat_id,
                    message_id=meeting.message_id,
                    text=message,
                )
            
            # Send DM to all participants
            for participant in participants:
                try:
                    dm_message = self._get_meeting_confirmed_dm(meeting, participant)
                    await self.telegram.send_dm(
                        user_id=participant.telegram_id,
                        text=dm_message,
                    )
                except Exception as e:
                    print(f"Failed to send DM to participant {participant.id}: {e}")
            
        except Exception as e:
            print(f"Failed to send meeting confirmed notification: {e}")
    
    async def send_meeting_canceled_notification(
        self,
        meeting: Meeting,
        organizer: User,
        participants: List[User],
        reason: Optional[str] = None,
    ) -> None:
        """Send notification when meeting is canceled."""
        try:
            message = self._get_meeting_canceled_message(meeting, organizer, reason)
            await self.telegram.send_message(
                chat_id=meeting.chat_id,
                text=message,
            )
            
            # Send DM to all participants
            for participant in participants:
                try:
                    dm_message = self._get_meeting_canceled_dm(meeting, participant, reason)
                    await self.telegram.send_dm(
                        user_id=participant.telegram_id,
                        text=dm_message,
                    )
                except Exception as e:
                    print(f"Failed to send DM to participant {participant.id}: {e}")
            
        except Exception as e:
            print(f"Failed to send meeting canceled notification: {e}")
    
    async def send_oauth_success_notification(
        self,
        user: User,
        meeting: Meeting,
    ) -> None:
        """Send notification when OAuth is successfully completed."""
        try:
            message = self._get_oauth_success_message(meeting, user)
            await self.telegram.send_dm(
                user_id=user.telegram_id,
                text=message,
            )
        except Exception as e:
            print(f"Failed to send OAuth success notification: {e}")
    
    async def send_oauth_failure_notification(
        self,
        user: User,
        meeting: Meeting,
        error: str,
    ) -> None:
        """Send notification when OAuth fails."""
        try:
            message = self._get_oauth_failure_message(meeting, user, error)
            await self.telegram.send_dm(
                user_id=user.telegram_id,
                text=message,
            )
        except Exception as e:
            print(f"Failed to send OAuth failure notification: {e}")
    
    def _get_oauth_consent_message(self, meeting: Meeting, user: User) -> str:
        """Get OAuth consent message."""
        return f"""
🔐 <b>Calendar Access Required</b>

Hi {user.first_name}! You've been invited to a meeting:

📅 <b>{meeting.topic}</b>
⏱ Duration: {meeting.duration_min} minutes

To participate in scheduling, you need to connect your Google Calendar.

Click the button below to authorize calendar access:
        """.strip()
    
    def _get_meeting_created_message(self, meeting: Meeting, organizer: User) -> str:
        """Get meeting created message."""
        return f"""
📅 <b>New Meeting Created</b>

<b>Topic:</b> {meeting.topic}
<b>Duration:</b> {meeting.duration_min} minutes
<b>Organizer:</b> {organizer.first_name}

Finding available time slots...
        """.strip()
    
    def _get_voting_message(self, meeting: Meeting, organizer: User, slots: List[tuple]) -> str:
        """Get voting message."""
        slots_text = ""
        for i, (start, end) in enumerate(slots):
            start_formatted = format_datetime(start, "UTC", "%Y-%m-%d %H:%M")
            end_formatted = format_datetime(end, "UTC", "%H:%M")
            slots_text += f"{i+1}. {start_formatted} - {end_formatted}\n"
        
        return f"""
🗳️ <b>Vote for Meeting Time</b>

<b>Topic:</b> {meeting.topic}
<b>Duration:</b> {meeting.duration_min} minutes
<b>Organizer:</b> {organizer.first_name}

<b>Available Time Slots:</b>
{slots_text}

Please vote on your preferred time slot:
✅ Yes - I can attend
❌ No - I cannot attend  
❓ Maybe - I might be able to attend
        """.strip()
    
    def _get_vote_received_message(
        self,
        meeting: Meeting,
        voter: User,
        slot_start: datetime,
        slot_end: datetime,
        vote_type: VoteType,
    ) -> str:
        """Get vote received message."""
        vote_emoji = {
            VoteType.YES: "✅",
            VoteType.NO: "❌",
            VoteType.MAYBE: "❓",
        }
        
        start_formatted = format_datetime(slot_start, "UTC", "%Y-%m-%d %H:%M")
        end_formatted = format_datetime(slot_end, "UTC", "%H:%M")
        
        return f"""
{vote_emoji[vote_type]} <b>{voter.first_name}</b> voted {vote_type.value} for:
{start_formatted} - {end_formatted}
        """.strip()
    
    def _get_meeting_confirmed_message(self, meeting: Meeting, organizer: User) -> str:
        """Get meeting confirmed message."""
        start_formatted = format_datetime(meeting.chosen_start_utc, "UTC", "%Y-%m-%d %H:%M")
        end_formatted = format_datetime(meeting.chosen_end_utc, "UTC", "%H:%M")
        
        return f"""
✅ <b>Meeting Confirmed!</b>

<b>Topic:</b> {meeting.topic}
<b>Time:</b> {start_formatted} - {end_formatted}
<b>Duration:</b> {meeting.duration_min} minutes
<b>Organizer:</b> {organizer.first_name}

The meeting has been added to your calendar.
        """.strip()
    
    def _get_meeting_confirmed_dm(self, meeting: Meeting, user: User) -> str:
        """Get meeting confirmed DM message."""
        start_formatted = format_datetime(meeting.chosen_start_utc, user.timezone, "%Y-%m-%d %H:%M")
        end_formatted = format_datetime(meeting.chosen_end_utc, user.timezone, "%H:%M")
        
        return f"""
✅ <b>Meeting Confirmed!</b>

<b>Topic:</b> {meeting.topic}
<b>Time:</b> {start_formatted} - {end_formatted} ({user.timezone})
<b>Duration:</b> {meeting.duration_min} minutes

The meeting has been added to your calendar.
        """.strip()
    
    def _get_meeting_canceled_message(
        self,
        meeting: Meeting,
        organizer: User,
        reason: Optional[str] = None,
    ) -> str:
        """Get meeting canceled message."""
        message = f"""
❌ <b>Meeting Canceled</b>

<b>Topic:</b> {meeting.topic}
<b>Organizer:</b> {organizer.first_name}
        """.strip()
        
        if reason:
            message += f"\n\n<b>Reason:</b> {reason}"
        
        return message
    
    def _get_meeting_canceled_dm(
        self,
        meeting: Meeting,
        user: User,
        reason: Optional[str] = None,
    ) -> str:
        """Get meeting canceled DM message."""
        message = f"""
❌ <b>Meeting Canceled</b>

<b>Topic:</b> {meeting.topic}
        """.strip()
        
        if reason:
            message += f"\n\n<b>Reason:</b> {reason}"
        
        return message
    
    def _get_oauth_success_message(self, meeting: Meeting, user: User) -> str:
        """Get OAuth success message."""
        return f"""
✅ <b>Calendar Connected Successfully!</b>

Your Google Calendar has been connected. You can now participate in meeting scheduling.

<b>Meeting:</b> {meeting.topic}
<b>Duration:</b> {meeting.duration_min} minutes

The organizer will be notified that you're ready to participate.
        """.strip()
    
    def _get_oauth_failure_message(self, meeting: Meeting, user: User, error: str) -> str:
        """Get OAuth failure message."""
        return f"""
❌ <b>Calendar Connection Failed</b>

Sorry, there was an error connecting your Google Calendar:

<b>Error:</b> {error}

Please try again or contact support if the problem persists.

<b>Meeting:</b> {meeting.topic}
        """.strip()
