"""Command handlers for the bot."""
import logging
from typing import List, Optional

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from models.user import User as DBUser
from models.meeting import Meeting
from services.scheduler import SchedulerService
from services.roster import RosterService
from services.notification import NotificationService
from providers.telegram import TelegramProvider
from bot.states import MeetingCreationStates
from bot.utils import (
    extract_duration_from_text,
    extract_topic_from_text,
    extract_mentions_from_text,
    format_user_mention,
    format_participant_list,
    get_meeting_creation_help,
    get_oauth_help,
    get_voting_help,
    validate_meeting_duration,
    validate_meeting_topic_length,
)

logger = logging.getLogger(__name__)

# Create router
router = Router()


@router.message(CommandStart())
async def start_command(message: Message, db_user: DBUser, db_session, state: FSMContext):
    """Handle /start command."""
    welcome_text = f"""
🎉 <b>Welcome to Meeting Scheduler Bot!</b>

Hi {db_user.first_name}! I help you schedule meetings with your team members.

<b>What I can do:</b>
• Create meetings with specific participants
• Find available time slots automatically
• Let everyone vote on preferred times
• Create calendar events automatically

<b>Quick Start:</b>
/meet 30 Team standup @alice @bob

<b>Need help?</b>
/help - Show all commands
/meet - Create a new meeting
/link_calendar - Connect your Google Calendar

Ready to schedule your first meeting? 🚀
    """.strip()
    
    await message.answer(welcome_text, parse_mode="HTML")


@router.message(Command("help"))
async def help_command(message: Message, db_user: DBUser):
    """Handle /help command."""
    help_text = f"""
🤖 <b>Meeting Scheduler Bot Help</b>

<b>Commands:</b>
/start - Welcome message and quick start
/help - Show this help message
/meet - Create a new meeting
/link_calendar - Connect your Google Calendar
/my_meetings - Show your meetings
/cancel - Cancel current operation

<b>Meeting Creation:</b>
/meet &lt;duration&gt; [topic] [@participants...]

<b>Examples:</b>
/meet 30 Team standup
/meet 1h Project planning @alice @bob
/meet 45min Code review @dev1 @dev2

<b>Duration formats:</b>
• 30 min, 30 minutes
• 1 hour, 2 hours  
• 1h, 2h

<b>Need more help?</b>
Use /meet to start creating a meeting, and I'll guide you through each step!
    """.strip()
    
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("meet"))
async def meet_command(message: Message, db_user: DBUser, db_session, state: FSMContext):
    """Handle /meet command."""
    # Parse command arguments
    command_text = message.text or ""
    
    # Extract duration
    duration = extract_duration_from_text(command_text)
    if not duration:
        await message.answer(
            "❌ Please specify a meeting duration.\n\n"
            "Examples:\n"
            "• /meet 30 Team standup\n"
            "• /meet 1h Project planning\n"
            "• /meet 45min Code review",
            parse_mode="HTML"
        )
        return
    
    # Validate duration
    if not validate_meeting_duration(duration):
        await message.answer(
            "❌ Meeting duration must be between 15 minutes and 8 hours.",
            parse_mode="HTML"
        )
        return
    
    # Extract topic
    topic = extract_topic_from_text(command_text)
    if not topic:
        await message.answer(
            f"📝 Great! You want to schedule a {duration}-minute meeting.\n\n"
            "What's the meeting about? Please provide a topic:",
            parse_mode="HTML"
        )
        await state.set_state(MeetingCreationStates.WAITING_FOR_TOPIC)
        await state.update_data(duration=duration)
        return
    
    # Validate topic
    if not validate_meeting_topic_length(topic):
        await message.answer(
            "❌ Meeting topic must be between 1 and 500 characters.",
            parse_mode="HTML"
        )
        return
    
    # Extract mentions
    mentions = extract_mentions_from_text(command_text)
    
    # Store meeting data
    await state.update_data(
        duration=duration,
        topic=topic,
        mentions=mentions,
    )
    
    # Check if we're in a group chat
    if message.chat.type in ["group", "supergroup"]:
        await handle_participant_selection(message, db_user, db_session, state)
    else:
        await message.answer(
            "❌ Meeting creation is only available in group chats.\n\n"
            "Please add me to a group and try again.",
            parse_mode="HTML"
        )


@router.message(MeetingCreationStates.WAITING_FOR_TOPIC)
async def handle_topic_input(message: Message, db_user: DBUser, db_session, state: FSMContext):
    """Handle topic input from user."""
    topic = message.text or ""
    
    # Validate topic
    if not validate_meeting_topic_length(topic):
        await message.answer(
            "❌ Meeting topic must be between 1 and 500 characters.\n\n"
            "Please try again:",
            parse_mode="HTML"
        )
        return
    
    # Get duration from state
    data = await state.get_data()
    duration = data.get("duration")
    
    # Update state with topic
    await state.update_data(topic=topic)
    
    # Check if we're in a group chat
    if message.chat.type in ["group", "supergroup"]:
        await handle_participant_selection(message, db_user, db_session, state)
    else:
        await message.answer(
            "❌ Meeting creation is only available in group chats.\n\n"
            "Please add me to a group and try again.",
            parse_mode="HTML"
        )


async def handle_participant_selection(
    message: Message,
    db_user: DBUser,
    db_session,
    state: FSMContext,
):
    """Handle participant selection for meeting."""
    # Get meeting data from state
    data = await state.get_data()
    duration = data.get("duration")
    topic = data.get("topic")
    mentions = data.get("mentions", [])
    
    # Get chat members
    roster_service = RosterService(db_session)
    chat_members = await roster_service.get_chat_members(message.chat.id)
    
    if not chat_members:
        await message.answer(
            "❌ No chat members found. Please make sure I can see the chat members.",
            parse_mode="HTML"
        )
        return
    
    # Filter out the bot user
    chat_members = [member for member in chat_members if member.telegram_id != message.from_user.id]
    
    if not chat_members:
        await message.answer(
            "❌ No other members found in this chat to invite to the meeting.",
            parse_mode="HTML"
        )
        return
    
    # Create participant selection message
    participant_text = f"""
📅 <b>Meeting Details</b>
<b>Topic:</b> {topic}
<b>Duration:</b> {duration} minutes
<b>Organizer:</b> {format_user_mention(db_user)}

👥 <b>Select Participants:</b>
Choose who should be invited to this meeting:
    """.strip()
    
    # Create participant selection keyboard
    from bot.keyboards.participants import create_participant_keyboard
    
    keyboard = create_participant_keyboard(chat_members, 0)  # meeting_id will be set later
    
    await message.answer(
        participant_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    
    # Update state
    await state.set_state(MeetingCreationStates.WAITING_FOR_PARTICIPANTS)
    await state.update_data(chat_members=chat_members)


@router.message(Command("link_calendar"))
async def link_calendar_command(message: Message, db_user: DBUser, db_session):
    """Handle /link_calendar command."""
    # Check if user already has OAuth token
    from models.oauth import OAuthToken
    from sqlalchemy import select, and_
    
    stmt = select(OAuthToken).where(
        and_(OAuthToken.user_id == db_user.id, OAuthToken.provider == "google")
    )
    result = await db_session.execute(stmt)
    existing_token = result.scalar_one_or_none()
    
    if existing_token and existing_token.is_active:
        await message.answer(
            "✅ Your Google Calendar is already connected!\n\n"
            "You can participate in meeting scheduling.\n\n"
            "To disconnect, contact support.",
            parse_mode="HTML"
        )
        return
    
    # Send OAuth consent message
    oauth_text = f"""
🔐 <b>Connect Google Calendar</b>

Hi {db_user.first_name}! To participate in meeting scheduling, you need to connect your Google Calendar.

<b>What this allows:</b>
• Check your availability automatically
• Create calendar events for confirmed meetings
• Receive meeting reminders

<b>Security:</b>
• Your calendar data is encrypted and secure
• Only meeting times are accessed
• You can revoke access anytime

Click the button below to connect your calendar:
    """.strip()
    
    # Create OAuth button
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔗 Connect Google Calendar",
            url="https://accounts.google.com/oauth/authorize",  # This would be the actual OAuth URL
        )
    )
    
    await message.answer(
        oauth_text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@router.message(Command("my_meetings"))
async def my_meetings_command(message: Message, db_user: DBUser, db_session):
    """Handle /my_meetings command."""
    # Get user's meetings
    scheduler_service = SchedulerService(db_session)
    meetings = await scheduler_service.get_user_meetings(db_user.id, limit=10)
    
    if not meetings:
        await message.answer(
            "📅 You don't have any meetings yet.\n\n"
            "Use /meet to create your first meeting!",
            parse_mode="HTML"
        )
        return
    
    # Format meetings list
    meetings_text = f"📅 <b>Your Meetings ({len(meetings)})</b>\n\n"
    
    for i, meeting in enumerate(meetings, 1):
        from bot.utils import format_meeting_summary
        meetings_text += f"{i}. {format_meeting_summary(meeting)}\n\n"
    
    await message.answer(meetings_text, parse_mode="HTML")


@router.message(Command("cancel"))
async def cancel_command(message: Message, db_user: DBUser, state: FSMContext):
    """Handle /cancel command."""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer(
            "❌ No active operation to cancel.",
            parse_mode="HTML"
        )
        return
    
    # Clear state
    await state.clear()
    
    await message.answer(
        "✅ Operation cancelled.\n\n"
        "You can start a new meeting with /meet",
        parse_mode="HTML"
    )


@router.message(Command("help_meet"))
async def help_meet_command(message: Message, db_user: DBUser):
    """Handle /help_meet command."""
    help_text = get_meeting_creation_help()
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("help_oauth"))
async def help_oauth_command(message: Message, db_user: DBUser):
    """Handle /help_oauth command."""
    help_text = get_oauth_help()
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("help_voting"))
async def help_voting_command(message: Message, db_user: DBUser):
    """Handle /help_voting command."""
    help_text = get_voting_help()
    await message.answer(help_text, parse_mode="HTML")


@router.message(F.text)
async def handle_text_message(message: Message, db_user: DBUser, state: FSMContext):
    """Handle general text messages."""
    current_state = await state.get_state()
    
    if current_state is None:
        # No active state, check if message looks like a meeting command
        if any(keyword in message.text.lower() for keyword in ["meeting", "schedule", "meet"]):
            await message.answer(
                "💡 Did you mean to create a meeting?\n\n"
                "Use /meet to start creating a meeting, or /help for more commands.",
                parse_mode="HTML"
            )
        return
    
    # Handle state-specific text input
    if current_state == MeetingCreationStates.WAITING_FOR_TOPIC:
        await handle_topic_input(message, db_user, message.bot.get("db_session"), state)
    else:
        await message.answer(
            "❓ I didn't understand that. Use /cancel to stop the current operation.",
            parse_mode="HTML"
        )
