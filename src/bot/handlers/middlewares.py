"""Bot middleware for authentication, logging, and error handling."""
import logging
import traceback
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject, Update
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_session
from services.roster import RosterService
from bot.utils import get_user_display_name

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging bot interactions."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Log bot interactions."""
        user = None
        chat_id = None
        event_type = type(event).__name__
        
        if isinstance(event, Message):
            user = event.from_user
            chat_id = event.chat.id
            text = event.text or event.caption or "[No text]"
            logger.info(
                f"Message from {get_user_display_name(user)} in chat {chat_id}: {text[:100]}"
            )
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            chat_id = event.message.chat.id if event.message else None
            callback_data = event.data or "[No data]"
            logger.info(
                f"Callback from {get_user_display_name(user)} in chat {chat_id}: {callback_data}"
            )
        
        # Add user info to data for handlers
        if user:
            data["telegram_user"] = user
            data["chat_id"] = chat_id
        
        return await handler(event, data)


class AuthMiddleware(BaseMiddleware):
    """Middleware for user authentication and registration."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Authenticate and register users."""
        user = data.get("telegram_user")
        if not user:
            return await handler(event, data)
        
        # Get database session
        async for session in get_session():
            try:
                # Register or update user
                roster_service = RosterService(session)
                db_user = await roster_service.get_or_create_user(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name or "",
                    last_name=user.last_name,
                )
                
                # Add user to data for handlers
                data["db_user"] = db_user
                data["db_session"] = session
                
                # Handle chat registration for group messages
                if isinstance(event, Message) and event.chat.type in ["group", "supergroup"]:
                    chat = event.chat
                    await roster_service.get_or_create_chat(
                        telegram_chat_id=chat.id,
                        title=chat.title or "Unknown Chat",
                        chat_type=chat.type,
                        description=getattr(chat, "description", None),
                    )
                    
                    # Add user to chat
                    await roster_service.add_user_to_chat(
                        user_id=db_user.id,
                        chat_id=chat.id,
                        role="member",
                    )
                
                return await handler(event, data)
                
            except Exception as e:
                logger.error(f"Auth middleware error: {e}", exc_info=True)
                return await handler(event, data)


class ErrorHandlerMiddleware(BaseMiddleware):
    """Middleware for handling errors."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Handle errors and provide user feedback."""
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Handler error: {e}", exc_info=True)
            
            # Try to send error message to user
            try:
                if isinstance(event, Message):
                    await event.answer(
                        "❌ An error occurred. Please try again or contact support.",
                        parse_mode="HTML",
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "❌ An error occurred. Please try again.",
                        show_alert=True,
                    )
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")
            
            # Re-raise the exception
            raise


class RateLimitMiddleware(BaseMiddleware):
    """Middleware for rate limiting."""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        """Initialize rate limit middleware."""
        self.max_requests = max_requests
        self.time_window = time_window
        self.user_requests = {}  # In production, use Redis
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Apply rate limiting."""
        user = data.get("telegram_user")
        if not user:
            return await handler(event, data)
        
        user_id = user.id
        current_time = data.get("event_time", 0)
        
        # Clean old requests
        if user_id in self.user_requests:
            self.user_requests[user_id] = [
                req_time for req_time in self.user_requests[user_id]
                if current_time - req_time < self.time_window
            ]
        else:
            self.user_requests[user_id] = []
        
        # Check rate limit
        if len(self.user_requests[user_id]) >= self.max_requests:
            if isinstance(event, Message):
                await event.answer(
                    "⚠️ Too many requests. Please wait a moment before trying again.",
                    parse_mode="HTML",
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "⚠️ Too many requests. Please wait a moment.",
                    show_alert=True,
                )
            return
        
        # Add current request
        self.user_requests[user_id].append(current_time)
        
        return await handler(event, data)


class StateMiddleware(BaseMiddleware):
    """Middleware for FSM state management."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Manage FSM state."""
        user = data.get("telegram_user")
        if not user:
            return await handler(event, data)
        
        # Get FSM context
        state: FSMContext = data.get("state")
        if state:
            # Add state info to data
            current_state = await state.get_state()
            data["current_state"] = current_state
            
            # Log state transitions
            if current_state:
                logger.debug(f"User {user.id} in state: {current_state}")
        
        return await handler(event, data)


class DatabaseMiddleware(BaseMiddleware):
    """Middleware for database session management."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Manage database sessions."""
        # Database session should already be provided by AuthMiddleware
        session: AsyncSession = data.get("db_session")
        if not session:
            logger.warning("No database session available")
        
        try:
            return await handler(event, data)
        except Exception as e:
            # Rollback transaction on error
            if session:
                await session.rollback()
            raise e


class ValidationMiddleware(BaseMiddleware):
    """Middleware for input validation."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Validate input data."""
        if isinstance(event, Message):
            # Validate message content
            if event.text:
                # Check for potentially harmful content
                if len(event.text) > 4000:  # Telegram message limit
                    await event.answer(
                        "❌ Message too long. Please keep it under 4000 characters.",
                        parse_mode="HTML",
                    )
                    return
                
                # Check for spam patterns
                if self._is_spam(event.text):
                    await event.answer(
                        "❌ Spam detected. Please use appropriate language.",
                        parse_mode="HTML",
                    )
                    return
        
        return await handler(event, data)
    
    def _is_spam(self, text: str) -> bool:
        """Check if text contains spam patterns."""
        spam_patterns = [
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            r'@\w+\s+@\w+\s+@\w+',  # Multiple mentions
            r'(.)\1{10,}',  # Repeated characters
        ]
        
        for pattern in spam_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False


