"""Telegram API wrapper for bot operations."""
from typing import Dict, Any, Optional, List
from datetime import datetime

import httpx
from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config.settings import get_settings
from providers.base import CalendarProviderError

settings = get_settings()


class TelegramProvider:
    """Telegram API wrapper for bot operations."""
    
    def __init__(self, bot_token: str):
        """Initialize Telegram provider with bot token."""
        self.bot_token = bot_token
        self.bot = Bot(token=bot_token)
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = True,
    ) -> Message:
        """Send a message to a chat."""
        try:
            return await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
        except Exception as e:
            raise CalendarProviderError(f"Failed to send message: {e}", "telegram")
    
    async def send_dm(
        self,
        user_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = "HTML",
    ) -> Message:
        """Send a direct message to a user."""
        return await self.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    
    async def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = "HTML",
    ) -> Message:
        """Edit message text."""
        try:
            return await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        except Exception as e:
            raise CalendarProviderError(f"Failed to edit message: {e}", "telegram")
    
    async def edit_message_reply_markup(
        self,
        chat_id: int,
        message_id: int,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> Message:
        """Edit message reply markup."""
        try:
            return await self.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=reply_markup,
            )
        except Exception as e:
            raise CalendarProviderError(f"Failed to edit message markup: {e}", "telegram")
    
    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False,
    ) -> bool:
        """Answer a callback query."""
        try:
            return await self.bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text=text,
                show_alert=show_alert,
            )
        except Exception as e:
            raise CalendarProviderError(f"Failed to answer callback query: {e}", "telegram")
    
    async def get_chat_member(self, chat_id: int, user_id: int) -> Dict[str, Any]:
        """Get chat member information."""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/getChatMember"
                params = {"chat_id": chat_id, "user_id": user_id}
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                result = response.json()
                if result["ok"]:
                    return result["result"]
                else:
                    raise CalendarProviderError(
                        f"Telegram API error: {result.get('description', 'Unknown error')}",
                        "telegram"
                    )
        except httpx.HTTPError as e:
            raise CalendarProviderError(f"Failed to get chat member: {e}", "telegram")
    
    async def get_chat(self, chat_id: int) -> Dict[str, Any]:
        """Get chat information."""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/getChat"
                params = {"chat_id": chat_id}
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                result = response.json()
                if result["ok"]:
                    return result["result"]
                else:
                    raise CalendarProviderError(
                        f"Telegram API error: {result.get('description', 'Unknown error')}",
                        "telegram"
                    )
        except httpx.HTTPError as e:
            raise CalendarProviderError(f"Failed to get chat: {e}", "telegram")
    
    async def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get user information."""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/getUser"
                params = {"user_id": user_id}
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                result = response.json()
                if result["ok"]:
                    return result["result"]
                else:
                    raise CalendarProviderError(
                        f"Telegram API error: {result.get('description', 'Unknown error')}",
                        "telegram"
                    )
        except httpx.HTTPError as e:
            raise CalendarProviderError(f"Failed to get user: {e}", "telegram")
    
    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        """Delete a message."""
        try:
            return await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            raise CalendarProviderError(f"Failed to delete message: {e}", "telegram")
    
    async def pin_message(self, chat_id: int, message_id: int) -> bool:
        """Pin a message."""
        try:
            return await self.bot.pin_chat_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            raise CalendarProviderError(f"Failed to pin message: {e}", "telegram")
    
    async def unpin_message(self, chat_id: int, message_id: int) -> bool:
        """Unpin a message."""
        try:
            return await self.bot.unpin_chat_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            raise CalendarProviderError(f"Failed to unpin message: {e}", "telegram")
    
    async def set_webhook(self, webhook_url: str, secret_token: Optional[str] = None) -> bool:
        """Set webhook for receiving updates."""
        try:
            return await self.bot.set_webhook(
                url=webhook_url,
                secret_token=secret_token,
            )
        except Exception as e:
            raise CalendarProviderError(f"Failed to set webhook: {e}", "telegram")
    
    async def delete_webhook(self) -> bool:
        """Delete webhook."""
        try:
            return await self.bot.delete_webhook()
        except Exception as e:
            raise CalendarProviderError(f"Failed to delete webhook: {e}", "telegram")
    
    async def get_webhook_info(self) -> Dict[str, Any]:
        """Get webhook information."""
        try:
            return await self.bot.get_webhook_info()
        except Exception as e:
            raise CalendarProviderError(f"Failed to get webhook info: {e}", "telegram")
    
    async def close(self):
        """Close the bot session."""
        await self.bot.session.close()


def create_inline_keyboard(buttons: List[List[Dict[str, Any]]]) -> InlineKeyboardMarkup:
    """Create an inline keyboard from button configuration."""
    keyboard = []
    
    for row in buttons:
        keyboard_row = []
        for button in row:
            keyboard_row.append(
                InlineKeyboardButton(
                    text=button["text"],
                    callback_data=button.get("callback_data"),
                    url=button.get("url"),
                )
            )
        keyboard.append(keyboard_row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_vote_keyboard(slots: List[tuple], meeting_id: int) -> InlineKeyboardMarkup:
    """Create voting keyboard for time slots."""
    buttons = []
    
    for i, (start_time, end_time) in enumerate(slots):
        # Create vote buttons for each slot
        slot_buttons = [
            {"text": "✅", "callback_data": f"vote:{meeting_id}:{i}:yes"},
            {"text": "❌", "callback_data": f"vote:{meeting_id}:{i}:no"},
            {"text": "❓", "callback_data": f"vote:{meeting_id}:{i}:maybe"},
        ]
        buttons.append(slot_buttons)
    
    # Add navigation buttons
    navigation_buttons = [
        {"text": "⏭ Next 5", "callback_data": f"next:{meeting_id}"},
        {"text": "✅ Confirm", "callback_data": f"confirm:{meeting_id}"},
    ]
    buttons.append(navigation_buttons)
    
    return create_inline_keyboard(buttons)


def create_participant_keyboard(participants: List[dict], meeting_id: int) -> InlineKeyboardMarkup:
    """Create participant selection keyboard."""
    buttons = []
    
    # Add participants in rows of 2
    for i in range(0, len(participants), 2):
        row = []
        for j in range(2):
            if i + j < len(participants):
                participant = participants[i + j]
                row.append({
                    "text": f"👤 {participant['first_name']}",
                    "callback_data": f"participant:{meeting_id}:{participant['id']}",
                })
        buttons.append(row)
    
    # Add action buttons
    action_buttons = [
        {"text": "✅ Done", "callback_data": f"participants_done:{meeting_id}"},
        {"text": "❌ Cancel", "callback_data": f"participants_cancel:{meeting_id}"},
    ]
    buttons.append(action_buttons)
    
    return create_inline_keyboard(buttons)
