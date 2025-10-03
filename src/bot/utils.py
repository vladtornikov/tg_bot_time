"""Bot utilities and helper functions."""
import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any

from aiogram.types import User, Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from models.user import User as DBUser
from models.meeting import Meeting
from models.vote import VoteType
from services.roster import RosterService
from utils.validation import validate_meeting_topic
from utils.timezone import format_datetime


def extract_duration_from_text(text: str) -> Optional[int]:
    """Extract meeting duration from text."""
    # Look for patterns like "30 min", "1 hour", "2h", etc.
    patterns = [
        r'(\d+)\s*(?:min|minute|minutes)',
        r'(\d+)\s*(?:hour|hours|hr|hrs)',
        r'(\d+)\s*h',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            duration = int(match.group(1))
            if 'hour' in pattern or 'hr' in pattern or 'h' in pattern:
                duration *= 60  # Convert hours to minutes
            return duration
    
    return None


def extract_topic_from_text(text: str) -> Optional[str]:
    """Extract meeting topic from text."""
    # Remove duration and command parts
    text = re.sub(r'/\w+', '', text)  # Remove command
    text = re.sub(r'\d+\s*(?:min|minute|minutes|hour|hours|hr|hrs|h)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'@\w+', '', text)  # Remove mentions
    
    # Clean up and return
    topic = text.strip()
    return topic if topic and validate_meeting_topic(topic) else None


def extract_mentions_from_text(text: str) -> List[str]:
    """Extract @mentions from text."""
    mentions = re.findall(r'@(\w+)', text)
    return mentions


def extract_user_ids_from_mentions(text: str) -> List[int]:
    """Extract user IDs from @mentions in text."""
    # This is a simplified version - in a real implementation,
    # you would need to resolve usernames to user IDs
    mentions = extract_mentions_from_text(text)
    # For now, return empty list - this would need proper username resolution
    return []


def format_user_mention(user: DBUser) -> str:
    """Format user for mention in messages."""
    if user.username:
        return f"@{user.username}"
    else:
        return f"<a href='tg://user?id={user.telegram_id}'>{user.first_name}</a>"


def format_participant_list(participants: List[DBUser]) -> str:
    """Format participant list for display."""
    if not participants:
        return "None"
    
    mentions = [format_user_mention(user) for user in participants]
    return ", ".join(mentions)


def format_time_slot(start: datetime, end: datetime, user_timezone: str = "UTC") -> str:
    """Format time slot for display."""
    start_formatted = format_datetime(start, user_timezone, "%Y-%m-%d %H:%M")
    end_formatted = format_datetime(end, user_timezone, "%H:%M")
    return f"{start_formatted} - {end_formatted}"


def format_vote_summary(votes: Dict[str, int], total_participants: int) -> str:
    """Format vote summary for display."""
    yes_votes = votes.get("yes", 0)
    no_votes = votes.get("no", 0)
    maybe_votes = votes.get("maybe", 0)
    
    participation_rate = (yes_votes + no_votes + maybe_votes) / total_participants if total_participants > 0 else 0
    
    return f"✅ {yes_votes} | ❌ {no_votes} | ❓ {maybe_votes} ({participation_rate:.1%})"


def parse_vote_callback_data(callback_data: str) -> Optional[Dict[str, Any]]:
    """Parse vote callback data."""
    # Format: "vote:{meeting_id}:{slot_index}:{vote_type}"
    parts = callback_data.split(":")
    if len(parts) != 4 or parts[0] != "vote":
        return None
    
    try:
        return {
            "meeting_id": int(parts[1]),
            "slot_index": int(parts[2]),
            "vote_type": parts[3],
        }
    except ValueError:
        return None


def parse_navigation_callback_data(callback_data: str) -> Optional[Dict[str, Any]]:
    """Parse navigation callback data."""
    # Format: "next:{meeting_id}" or "confirm:{meeting_id}"
    parts = callback_data.split(":")
    if len(parts) != 2:
        return None
    
    try:
        return {
            "action": parts[0],
            "meeting_id": int(parts[1]),
        }
    except ValueError:
        return None


def parse_participant_callback_data(callback_data: str) -> Optional[Dict[str, Any]]:
    """Parse participant callback data."""
    # Format: "participant:{meeting_id}:{user_id}"
    parts = callback_data.split(":")
    if len(parts) != 3 or parts[0] != "participant":
        return None
    
    try:
        return {
            "meeting_id": int(parts[1]),
            "user_id": int(parts[2]),
        }
    except ValueError:
        return None


def get_user_display_name(user: User) -> str:
    """Get display name for Telegram user."""
    if user.username:
        return f"@{user.username}"
    elif user.first_name:
        return user.first_name
    else:
        return "Unknown User"


def is_user_admin(user: User, chat_id: int) -> bool:
    """Check if user is admin in chat."""
    # This is a simplified version - in a real implementation,
    # you would check the user's role in the chat
    return False


def validate_meeting_duration(duration: int) -> bool:
    """Validate meeting duration."""
    return 15 <= duration <= 480  # 15 minutes to 8 hours


def validate_meeting_topic_length(topic: str) -> bool:
    """Validate meeting topic length."""
    return 1 <= len(topic) <= 500


def get_meeting_state_description(state: str) -> str:
    """Get human-readable description of meeting state."""
    descriptions = {
        "draft": "Draft",
        "awaiting_consent": "Waiting for calendar access",
        "resolving": "Finding available times",
        "voting": "Voting in progress",
        "confirmed": "Confirmed",
        "failed": "Failed",
        "canceled": "Canceled",
    }
    return descriptions.get(state, "Unknown")


def format_meeting_summary(meeting: Meeting) -> str:
    """Format meeting summary for display."""
    state_desc = get_meeting_state_description(meeting.state.value)
    
    summary = f"""
📅 <b>{meeting.topic}</b>
⏱ Duration: {meeting.duration_min} minutes
📊 Status: {state_desc}
    """.strip()
    
    if meeting.chosen_start_utc and meeting.chosen_end_utc:
        time_str = format_time_slot(meeting.chosen_start_utc, meeting.chosen_end_utc)
        summary += f"\n🕐 Time: {time_str}"
    
    return summary


def get_vote_emoji(vote_type: VoteType) -> str:
    """Get emoji for vote type."""
    emojis = {
        VoteType.YES: "✅",
        VoteType.NO: "❌",
        VoteType.MAYBE: "❓",
    }
    return emojis.get(vote_type, "❓")


def format_vote_button_text(vote_type: VoteType, count: int = 0) -> str:
    """Format vote button text."""
    emoji = get_vote_emoji(vote_type)
    if count > 0:
        return f"{emoji} {count}"
    else:
        return emoji


def get_working_hours_description(start_hour: int, end_hour: int) -> str:
    """Get working hours description."""
    return f"{start_hour:02d}:00 - {end_hour:02d}:00"


def format_timezone_info(timezone_str: str) -> str:
    """Format timezone information."""
    return f"({timezone_str})"


def get_meeting_creation_help() -> str:
    """Get help text for meeting creation."""
    return """
📅 <b>Meeting Creation Help</b>

<b>Commands:</b>
/meet &lt;duration&gt; [topic] [@participants...]

<b>Examples:</b>
/meet 30 Team standup
/meet 1h Project planning @alice @bob
/meet 45min Code review @dev1 @dev2

<b>Duration formats:</b>
• 30 min, 30 minutes
• 1 hour, 2 hours
• 1h, 2h

<b>Notes:</b>
• Duration: 15 minutes to 8 hours
• Topic: 1-500 characters
• Participants: @mention users in the chat
    """.strip()


def get_oauth_help() -> str:
    """Get help text for OAuth."""
    return """
🔐 <b>Calendar Access Help</b>

To participate in meeting scheduling, you need to connect your Google Calendar.

<b>Steps:</b>
1. Click the "Connect Calendar" button
2. Sign in to your Google account
3. Grant calendar access permissions
4. Return to Telegram

<b>Permissions needed:</b>
• Read calendar events
• Create calendar events

<b>Security:</b>
• Your calendar data is encrypted
• Only meeting times are accessed
• You can revoke access anytime
    """.strip()


def get_voting_help() -> str:
    """Get help text for voting."""
    return """
🗳️ <b>Voting Help</b>

<b>Vote options:</b>
✅ Yes - I can attend at this time
❌ No - I cannot attend at this time
❓ Maybe - I might be able to attend

<b>Navigation:</b>
⏭ Next 5 - Show more time options
✅ Confirm - Confirm the selected time

<b>Tips:</b>
• Vote on all time slots you're considering
• The organizer will see all votes
• You can change your vote anytime
    """.strip()
