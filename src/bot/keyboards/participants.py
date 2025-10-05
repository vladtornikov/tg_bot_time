"""Participant selection keyboard components."""
from typing import List, Dict, Any

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models.user import User
from bot.utils import format_user_mention


def create_participant_keyboard(
    participants: List[User],
    meeting_id: int,
    selected_participants: List[int] = None,
    max_participants: int = 30,
) -> InlineKeyboardMarkup:
    """Create participant selection keyboard."""
    if selected_participants is None:
        selected_participants = []
    
    builder = InlineKeyboardBuilder()
    
    # Add participants in rows of 2
    for i in range(0, len(participants), 2):
        row_buttons = []
        
        for j in range(2):
            if i + j < len(participants):
                participant = participants[i + j]
                is_selected = participant.id in selected_participants
                
                # Format button text
                if is_selected:
                    text = f"✅ {participant.first_name}"
                else:
                    text = f"👤 {participant.first_name}"
                
                row_buttons.append(
                    InlineKeyboardButton(
                        text=text,
                        callback_data=f"toggle_participant:{meeting_id}:{participant.id}",
                    )
                )
        
        if row_buttons:
            builder.row(*row_buttons)
    
    # Add action buttons
    action_buttons = []
    
    if selected_participants:
        action_buttons.append(
            InlineKeyboardButton(
                text=f"✅ Done ({len(selected_participants)} selected)",
                callback_data=f"participants_done:{meeting_id}",
            )
        )
    
    action_buttons.append(
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data=f"participants_cancel:{meeting_id}",
        )
    )
    
    if action_buttons:
        builder.row(*action_buttons)
    
    # Add select all/none buttons if there are many participants
    if len(participants) > 5:
        builder.row(
            InlineKeyboardButton(
                text="✅ Select All",
                callback_data=f"select_all:{meeting_id}",
            ),
            InlineKeyboardButton(
                text="❌ Select None",
                callback_data=f"select_none:{meeting_id}",
            ),
        )
    
    return builder.as_markup()


def create_participant_confirmation_keyboard(
    meeting_id: int,
    selected_participants: List[User],
) -> InlineKeyboardMarkup:
    """Create keyboard for confirming participant selection."""
    builder = InlineKeyboardBuilder()
    
    # Show selected participants
    for participant in selected_participants:
        builder.row(
            InlineKeyboardButton(
                text=f"👤 {participant.first_name}",
                callback_data=f"view_participant:{meeting_id}:{participant.id}",
            )
        )
    
    # Add action buttons
    builder.row(
        InlineKeyboardButton(
            text="✅ Confirm Participants",
            callback_data=f"confirm_participants:{meeting_id}",
        ),
        InlineKeyboardButton(
            text="✏️ Edit Selection",
            callback_data=f"edit_participants:{meeting_id}",
        ),
    )
    
    return builder.as_markup()


def create_participant_management_keyboard(
    meeting_id: int,
    participants: List[User],
    selected_participants: List[int] = None,
) -> InlineKeyboardMarkup:
    """Create keyboard for managing participants."""
    if selected_participants is None:
        selected_participants = []
    
    builder = InlineKeyboardBuilder()
    
    # Add participants with management options
    for participant in participants:
        is_selected = participant.id in selected_participants
        
        # Format button text
        if is_selected:
            text = f"✅ {participant.first_name}"
        else:
            text = f"👤 {participant.first_name}"
        
        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"manage_participant:{meeting_id}:{participant.id}",
            )
        )
    
    # Add bulk actions
    builder.row(
        InlineKeyboardButton(
            text="✅ Select All",
            callback_data=f"bulk_select_all:{meeting_id}",
        ),
        InlineKeyboardButton(
            text="❌ Clear All",
            callback_data=f"bulk_clear_all:{meeting_id}",
        ),
    )
    
    # Add final actions
    builder.row(
        InlineKeyboardButton(
            text="✅ Done",
            callback_data=f"participants_final:{meeting_id}",
        ),
        InlineKeyboardButton(
            text="❌ Cancel",
            callback_data=f"participants_cancel:{meeting_id}",
        ),
    )
    
    return builder.as_markup()


def create_participant_info_keyboard(
    meeting_id: int,
    participant: User,
    is_selected: bool = False,
) -> InlineKeyboardMarkup:
    """Create keyboard for participant information."""
    builder = InlineKeyboardBuilder()
    
    # Show participant info
    info_text = f"👤 {participant.first_name}"
    if participant.username:
        info_text += f" (@{participant.username})"
    
    builder.row(
        InlineKeyboardButton(
            text=info_text,
            callback_data=f"participant_info:{meeting_id}:{participant.id}",
        )
    )
    
    # Add selection toggle
    if is_selected:
        builder.row(
            InlineKeyboardButton(
                text="❌ Remove from Meeting",
                callback_data=f"remove_participant:{meeting_id}:{participant.id}",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Add to Meeting",
                callback_data=f"add_participant:{meeting_id}:{participant.id}",
            )
        )
    
    # Add back button
    builder.row(
        InlineKeyboardButton(
            text="🔙 Back to Selection",
            callback_data=f"back_to_selection:{meeting_id}",
        )
    )
    
    return builder.as_markup()


def create_participant_search_keyboard(
    meeting_id: int,
    search_query: str = "",
) -> InlineKeyboardMarkup:
    """Create keyboard for participant search."""
    builder = InlineKeyboardBuilder()
    
    # Add search input button
    builder.row(
        InlineKeyboardButton(
            text=f"🔍 Search: {search_query or 'Enter username...'}",
            callback_data=f"search_participants:{meeting_id}",
        )
    )
    
    # Add quick filters
    builder.row(
        InlineKeyboardButton(
            text="👥 All Members",
            callback_data=f"filter_all:{meeting_id}",
        ),
        InlineKeyboardButton(
            text="👑 Admins Only",
            callback_data=f"filter_admins:{meeting_id}",
        ),
    )
    
    # Add back button
    builder.row(
        InlineKeyboardButton(
            text="🔙 Back to Selection",
            callback_data=f"back_to_selection:{meeting_id}",
        )
    )
    
    return builder.as_markup()


def create_participant_help_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for participant selection help."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📖 How to Select",
            callback_data="participant_help",
        ),
        InlineKeyboardButton(
            text="❓ Selection Rules",
            callback_data="selection_rules",
        ),
    )
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 Back to Selection",
            callback_data="back_to_selection",
        )
    )
    
    return builder.as_markup()


