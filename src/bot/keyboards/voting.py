"""Voting keyboard components."""
from typing import List, Tuple
from datetime import datetime

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils import format_vote_button_text, get_vote_emoji
from models.vote import VoteType


def create_vote_keyboard(
    slots: List[Tuple[datetime, datetime]],
    meeting_id: int,
    votes: dict = None,
    has_next: bool = False,
) -> InlineKeyboardMarkup:
    """Create voting keyboard for time slots."""
    builder = InlineKeyboardBuilder()
    
    for i, (start_time, end_time) in enumerate(slots):
        # Create vote buttons for each slot
        slot_votes = votes.get(i, {}) if votes else {}
        
        yes_count = slot_votes.get("yes", 0)
        no_count = slot_votes.get("no", 0)
        maybe_count = slot_votes.get("maybe", 0)
        
        # Add vote buttons in a row
        builder.row(
            InlineKeyboardButton(
                text=format_vote_button_text(VoteType.YES, yes_count),
                callback_data=f"vote:{meeting_id}:{i}:yes",
            ),
            InlineKeyboardButton(
                text=format_vote_button_text(VoteType.NO, no_count),
                callback_data=f"vote:{meeting_id}:{i}:no",
            ),
            InlineKeyboardButton(
                text=format_vote_button_text(VoteType.MAYBE, maybe_count),
                callback_data=f"vote:{meeting_id}:{i}:maybe",
            ),
        )
    
    # Add navigation buttons
    navigation_buttons = []
    
    if has_next:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="⏭ Next 5",
                callback_data=f"next:{meeting_id}",
            )
        )
    
    navigation_buttons.append(
        InlineKeyboardButton(
            text="✅ Confirm Selection",
            callback_data=f"confirm:{meeting_id}",
        )
    )
    
    if navigation_buttons:
        builder.row(*navigation_buttons)
    
    # Add cancel button
    builder.row(
        InlineKeyboardButton(
            text="❌ Cancel Meeting",
            callback_data=f"cancel:{meeting_id}",
        )
    )
    
    return builder.as_markup()


def create_slot_selection_keyboard(
    meeting_id: int,
    selected_slot: int = None,
) -> InlineKeyboardMarkup:
    """Create keyboard for selecting a specific time slot."""
    builder = InlineKeyboardBuilder()
    
    # Add selection buttons for each slot
    for i in range(5):  # Assuming 5 slots
        text = f"Slot {i+1}"
        if selected_slot == i:
            text = f"✅ {text}"
        
        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"select_slot:{meeting_id}:{i}",
            )
        )
    
    # Add action buttons
    builder.row(
        InlineKeyboardButton(
            text="✅ Confirm This Time",
            callback_data=f"confirm_slot:{meeting_id}",
        ),
        InlineKeyboardButton(
            text="⏭ Show More Options",
            callback_data=f"more_slots:{meeting_id}",
        ),
    )
    
    return builder.as_markup()


def create_voting_results_keyboard(
    meeting_id: int,
    results: List[dict],
) -> InlineKeyboardMarkup:
    """Create keyboard for displaying voting results."""
    builder = InlineKeyboardBuilder()
    
    # Sort results by yes votes (descending)
    sorted_results = sorted(results, key=lambda x: x["votes"].get("yes", 0), reverse=True)
    
    for i, result in enumerate(sorted_results[:5]):  # Show top 5
        slot_start = result["slot_start"]
        slot_end = result["slot_end"]
        votes = result["votes"]
        
        yes_votes = votes.get("yes", 0)
        no_votes = votes.get("no", 0)
        maybe_votes = votes.get("maybe", 0)
        
        # Format time slot
        time_str = f"{slot_start.strftime('%m/%d %H:%M')} - {slot_end.strftime('%H:%M')}"
        
        # Format vote summary
        vote_summary = f"✅{yes_votes} ❌{no_votes} ❓{maybe_votes}"
        
        builder.row(
            InlineKeyboardButton(
                text=f"{i+1}. {time_str} ({vote_summary})",
                callback_data=f"select_result:{meeting_id}:{i}",
            )
        )
    
    # Add action buttons
    builder.row(
        InlineKeyboardButton(
            text="✅ Confirm Best Option",
            callback_data=f"confirm_best:{meeting_id}",
        ),
        InlineKeyboardButton(
            text="⏭ Show More Results",
            callback_data=f"more_results:{meeting_id}",
        ),
    )
    
    return builder.as_markup()


def create_meeting_confirmation_keyboard(
    meeting_id: int,
    slot_start: datetime,
    slot_end: datetime,
) -> InlineKeyboardMarkup:
    """Create keyboard for meeting confirmation."""
    builder = InlineKeyboardBuilder()
    
    # Format time slot
    time_str = f"{slot_start.strftime('%Y-%m-%d %H:%M')} - {slot_end.strftime('%H:%M')}"
    
    builder.row(
        InlineKeyboardButton(
            text=f"✅ Confirm: {time_str}",
            callback_data=f"final_confirm:{meeting_id}",
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="❌ Cancel Meeting",
            callback_data=f"final_cancel:{meeting_id}",
        )
    )
    
    return builder.as_markup()


def create_voting_help_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for voting help."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📖 How to Vote",
            callback_data="voting_help",
        ),
        InlineKeyboardButton(
            text="❓ Vote Meanings",
            callback_data="vote_meanings",
        ),
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 Back to Voting",
            callback_data="back_to_voting",
        )
    )
    
    return builder.as_markup()


def create_vote_type_keyboard(
    meeting_id: int,
    slot_index: int,
    current_vote: VoteType = None,
) -> InlineKeyboardMarkup:
    """Create keyboard for selecting vote type."""
    builder = InlineKeyboardBuilder()
    
    vote_types = [
        (VoteType.YES, "✅ Yes - I can attend"),
        (VoteType.NO, "❌ No - I cannot attend"),
        (VoteType.MAYBE, "❓ Maybe - I might attend"),
    ]
    
    for vote_type, description in vote_types:
        text = description
        if current_vote == vote_type:
            text = f"✓ {description}"
        
        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"set_vote:{meeting_id}:{slot_index}:{vote_type.value}",
            )
        )
    
    # Add back button
    builder.row(
        InlineKeyboardButton(
            text="🔙 Back to Slots",
            callback_data=f"back_to_slots:{meeting_id}",
        )
    )
    
    return builder.as_markup()


