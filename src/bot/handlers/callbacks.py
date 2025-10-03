"""Callback query handlers for the bot."""
import logging
from typing import List, Optional

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from models.user import User as DBUser
from models.meeting import Meeting
from models.vote import VoteType
from services.scheduler import SchedulerService
from services.roster import RosterService
from services.notification import NotificationService
from providers.telegram import TelegramProvider
from bot.states import MeetingCreationStates
from bot.utils import (
    parse_vote_callback_data,
    parse_navigation_callback_data,
    parse_participant_callback_data,
    format_time_slot,
    format_participant_list,
    get_vote_emoji,
)

logger = logging.getLogger(__name__)

# Create router
router = Router()


@router.callback_query(F.data.startswith("vote:"))
async def handle_vote_callback(callback: CallbackQuery, db_user: DBUser, db_session):
    """Handle vote callback queries."""
    # Parse callback data
    vote_data = parse_vote_callback_data(callback.data)
    if not vote_data:
        await callback.answer("❌ Invalid vote data", show_alert=True)
        return
    
    meeting_id = vote_data["meeting_id"]
    slot_index = vote_data["slot_index"]
    vote_type_str = vote_data["vote_type"]
    
    # Convert vote type string to enum
    try:
        vote_type = VoteType(vote_type_str)
    except ValueError:
        await callback.answer("❌ Invalid vote type", show_alert=True)
        return
    
    # Get meeting
    scheduler_service = SchedulerService(db_session)
    meeting = await scheduler_service.get_meeting(meeting_id)
    
    if not meeting:
        await callback.answer("❌ Meeting not found", show_alert=True)
        return
    
    # Check if user is a participant
    is_participant = any(
        participant.user_id == db_user.id
        for participant in meeting.participants
    )
    
    if not is_participant:
        await callback.answer("❌ You're not a participant in this meeting", show_alert=True)
        return
    
    # Get time slots from meeting data (this would be stored in the meeting or retrieved)
    # For now, we'll assume slots are stored in the meeting or retrieved from somewhere
    # In a real implementation, you'd store the current voting slots in the meeting or state
    
    # Cast vote
    try:
        # This is a simplified version - in reality, you'd need to get the actual slot times
        from datetime import datetime, timezone, timedelta
        base_time = datetime.now(timezone.utc)
        slot_start = base_time + timedelta(hours=slot_index)
        slot_end = slot_start + timedelta(minutes=meeting.duration_min)
        
        vote = await scheduler_service.cast_vote(
            meeting_id=meeting_id,
            user_id=db_user.id,
            slot_start=slot_start,
            slot_end=slot_end,
            vote_type=vote_type,
        )
        
        # Send confirmation
        emoji = get_vote_emoji(vote_type)
        await callback.answer(f"{emoji} Vote recorded: {vote_type.value}")
        
        # Update voting interface
        await update_voting_interface(callback, meeting_id, db_session)
        
    except Exception as e:
        logger.error(f"Error casting vote: {e}")
        await callback.answer("❌ Failed to record vote", show_alert=True)


@router.callback_query(F.data.startswith("next:"))
async def handle_next_callback(callback: CallbackQuery, db_user: DBUser, db_session):
    """Handle next batch callback queries."""
    # Parse callback data
    nav_data = parse_navigation_callback_data(callback.data)
    if not nav_data or nav_data["action"] != "next":
        await callback.answer("❌ Invalid navigation data", show_alert=True)
        return
    
    meeting_id = nav_data["meeting_id"]
    
    # Get meeting
    scheduler_service = SchedulerService(db_session)
    meeting = await scheduler_service.get_meeting(meeting_id)
    
    if not meeting:
        await callback.answer("❌ Meeting not found", show_alert=True)
        return
    
    # Get next batch of time slots
    try:
        # This would get the next 5 slots from the scheduler
        # For now, we'll simulate this
        await callback.answer("⏭ Loading next 5 time slots...")
        
        # Update the voting interface with next batch
        await update_voting_interface(callback, meeting_id, db_session, next_batch=True)
        
    except Exception as e:
        logger.error(f"Error loading next batch: {e}")
        await callback.answer("❌ Failed to load next batch", show_alert=True)


@router.callback_query(F.data.startswith("confirm:"))
async def handle_confirm_callback(callback: CallbackQuery, db_user: DBUser, db_session):
    """Handle confirm callback queries."""
    # Parse callback data
    nav_data = parse_navigation_callback_data(callback.data)
    if not nav_data or nav_data["action"] != "confirm":
        await callback.answer("❌ Invalid confirmation data", show_alert=True)
        return
    
    meeting_id = nav_data["meeting_id"]
    
    # Get meeting
    scheduler_service = SchedulerService(db_session)
    meeting = await scheduler_service.get_meeting(meeting_id)
    
    if not meeting:
        await callback.answer("❌ Meeting not found", show_alert=True)
        return
    
    # Check if user is the organizer
    if meeting.organizer_id != db_user.id:
        await callback.answer("❌ Only the organizer can confirm the meeting", show_alert=True)
        return
    
    # Get voting results and find best slot
    try:
        # This would get the actual voting results
        # For now, we'll simulate finding the best slot
        from datetime import datetime, timezone, timedelta
        
        # Simulate best slot (in reality, this would be calculated from votes)
        best_start = datetime.now(timezone.utc) + timedelta(hours=1)
        best_end = best_start + timedelta(minutes=meeting.duration_min)
        
        # Confirm meeting
        event_id = await scheduler_service.confirm_meeting(
            meeting_id=meeting_id,
            chosen_start=best_start,
            chosen_end=best_end,
        )
        
        await callback.answer("✅ Meeting confirmed and calendar event created!")
        
        # Update message to show confirmation
        await update_meeting_confirmation(callback, meeting, best_start, best_end)
        
    except Exception as e:
        logger.error(f"Error confirming meeting: {e}")
        await callback.answer("❌ Failed to confirm meeting", show_alert=True)


@router.callback_query(F.data.startswith("cancel:"))
async def handle_cancel_callback(callback: CallbackQuery, db_user: DBUser, db_session):
    """Handle cancel callback queries."""
    # Parse callback data
    nav_data = parse_navigation_callback_data(callback.data)
    if not nav_data or nav_data["action"] != "cancel":
        await callback.answer("❌ Invalid cancellation data", show_alert=True)
        return
    
    meeting_id = nav_data["meeting_id"]
    
    # Get meeting
    scheduler_service = SchedulerService(db_session)
    meeting = await scheduler_service.get_meeting(meeting_id)
    
    if not meeting:
        await callback.answer("❌ Meeting not found", show_alert=True)
        return
    
    # Check if user is the organizer
    if meeting.organizer_id != db_user.id:
        await callback.answer("❌ Only the organizer can cancel the meeting", show_alert=True)
        return
    
    # Cancel meeting
    try:
        success = await scheduler_service.cancel_meeting(meeting_id, "Cancelled by organizer")
        
        if success:
            await callback.answer("❌ Meeting cancelled")
            await update_meeting_cancellation(callback, meeting)
        else:
            await callback.answer("❌ Failed to cancel meeting", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error cancelling meeting: {e}")
        await callback.answer("❌ Failed to cancel meeting", show_alert=True)


@router.callback_query(F.data.startswith("toggle_participant:"))
async def handle_participant_toggle_callback(callback: CallbackQuery, db_user: DBUser, db_session, state: FSMContext):
    """Handle participant toggle callback queries."""
    # Parse callback data
    parts = callback.data.split(":")
    if len(parts) != 3 or parts[0] != "toggle_participant":
        await callback.answer("❌ Invalid participant data", show_alert=True)
        return
    
    try:
        meeting_id = int(parts[1])
        participant_id = int(parts[2])
    except ValueError:
        await callback.answer("❌ Invalid participant ID", show_alert=True)
        return
    
    # Get current state data
    data = await state.get_data()
    selected_participants = data.get("selected_participants", [])
    
    # Toggle participant selection
    if participant_id in selected_participants:
        selected_participants.remove(participant_id)
        action = "removed"
    else:
        selected_participants.append(participant_id)
        action = "added"
    
    # Update state
    await state.update_data(selected_participants=selected_participants)
    
    # Update keyboard
    await update_participant_keyboard(callback, meeting_id, selected_participants, db_session)
    
    # Send feedback
    await callback.answer(f"👤 Participant {action}")


@router.callback_query(F.data.startswith("participants_done:"))
async def handle_participants_done_callback(callback: CallbackQuery, db_user: DBUser, db_session, state: FSMContext):
    """Handle participants done callback queries."""
    # Parse callback data
    parts = callback.data.split(":")
    if len(parts) != 2 or parts[0] != "participants_done":
        await callback.answer("❌ Invalid participants data", show_alert=True)
        return
    
    try:
        meeting_id = int(parts[1])
    except ValueError:
        await callback.answer("❌ Invalid meeting ID", show_alert=True)
        return
    
    # Get current state data
    data = await state.get_data()
    selected_participants = data.get("selected_participants", [])
    
    if not selected_participants:
        await callback.answer("❌ Please select at least one participant", show_alert=True)
        return
    
    # Create meeting
    try:
        scheduler_service = SchedulerService(db_session)
        
        # Get meeting data from state
        duration = data.get("duration")
        topic = data.get("topic")
        chat_members = data.get("chat_members", [])
        
        # Filter selected participants
        selected_users = [
            user for user in chat_members
            if user.id in selected_participants
        ]
        
        # Create meeting
        meeting = await scheduler_service.create_meeting(
            organizer_id=db_user.id,
            chat_id=callback.message.chat.id,
            topic=topic,
            duration_min=duration,
            participant_telegram_ids=[user.telegram_id for user in selected_users],
        )
        
        await callback.answer("✅ Meeting created successfully!")
        
        # Update message to show meeting creation
        await update_meeting_creation(callback, meeting, selected_users)
        
        # Clear state
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error creating meeting: {e}")
        await callback.answer("❌ Failed to create meeting", show_alert=True)


@router.callback_query(F.data.startswith("participants_cancel:"))
async def handle_participants_cancel_callback(callback: CallbackQuery, db_user: DBUser, state: FSMContext):
    """Handle participants cancel callback queries."""
    # Clear state
    await state.clear()
    
    await callback.answer("❌ Meeting creation cancelled")
    await callback.message.edit_text(
        "❌ Meeting creation cancelled.\n\n"
        "Use /meet to create a new meeting.",
        parse_mode="HTML"
    )


async def update_voting_interface(callback: CallbackQuery, meeting_id: int, db_session, next_batch: bool = False):
    """Update the voting interface with current votes."""
    # This would update the voting keyboard with current vote counts
    # For now, we'll just acknowledge the update
    pass


async def update_meeting_confirmation(callback: CallbackQuery, meeting: Meeting, start_time, end_time):
    """Update message to show meeting confirmation."""
    confirmation_text = f"""
✅ <b>Meeting Confirmed!</b>

<b>Topic:</b> {meeting.topic}
<b>Time:</b> {format_time_slot(start_time, end_time)}
<b>Duration:</b> {meeting.duration_min} minutes

The meeting has been added to everyone's calendar.
    """.strip()
    
    await callback.message.edit_text(
        confirmation_text,
        parse_mode="HTML"
    )


async def update_meeting_cancellation(callback: CallbackQuery, meeting: Meeting):
    """Update message to show meeting cancellation."""
    cancellation_text = f"""
❌ <b>Meeting Cancelled</b>

<b>Topic:</b> {meeting.topic}
<b>Reason:</b> Cancelled by organizer

The meeting has been cancelled.
    """.strip()
    
    await callback.message.edit_text(
        cancellation_text,
        parse_mode="HTML"
    )


async def update_participant_keyboard(callback: CallbackQuery, meeting_id: int, selected_participants: List[int], db_session):
    """Update participant selection keyboard."""
    # Get chat members
    roster_service = RosterService(db_session)
    chat_members = await roster_service.get_chat_members(callback.message.chat.id)
    
    # Filter out the bot user
    chat_members = [member for member in chat_members if member.telegram_id != callback.from_user.id]
    
    # Create updated keyboard
    from bot.keyboards.participants import create_participant_keyboard
    keyboard = create_participant_keyboard(chat_members, meeting_id, selected_participants)
    
    # Update message
    await callback.message.edit_reply_markup(reply_markup=keyboard)


async def update_meeting_creation(callback: CallbackQuery, meeting: Meeting, participants: List):
    """Update message to show meeting creation."""
    participant_list = format_participant_list(participants)
    
    creation_text = f"""
📅 <b>Meeting Created!</b>

<b>Topic:</b> {meeting.topic}
<b>Duration:</b> {meeting.duration_min} minutes
<b>Participants:</b> {participant_list}
<b>Status:</b> {meeting.state.value.title()}

The system is now finding available time slots...
    """.strip()
    
    await callback.message.edit_text(
        creation_text,
        parse_mode="HTML"
    )
