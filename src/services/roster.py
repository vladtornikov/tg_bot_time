"""Roster service for user and chat management."""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.user import User, Chat, ChatMembership
from models.meeting import MeetingParticipant
from utils.validation import validate_telegram_username, validate_timezone
from utils.timezone import get_user_timezone


class RosterService:
    """Service for managing users and chat memberships."""
    
    def __init__(self, db_session: AsyncSession):
        """Initialize roster service with database session."""
        self.db = db_session
    
    async def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: str = "",
        last_name: Optional[str] = None,
    ) -> User:
        """Get existing user or create new one."""
        # Try to find existing user
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            # Update user information if provided
            if username and validate_telegram_username(username):
                user.username = username
            if first_name:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name
            user.updated_at = datetime.now(timezone.utc)
            await self.db.commit()
            return user
        
        # Create new user
        user = User(
            telegram_id=telegram_id,
            username=username if validate_telegram_username(username) else None,
            first_name=first_name,
            last_name=last_name,
            timezone="UTC",
            working_hours_start=8,
            working_hours_end=20,
            is_active=True,
            is_bot=False,
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by internal ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        if not validate_telegram_username(username):
            return None
        
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_user_timezone(self, user_id: int, timezone_str: str) -> bool:
        """Update user timezone."""
        if not validate_timezone(timezone_str):
            return False
        
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.timezone = timezone_str
        user.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        return True
    
    async def update_user_working_hours(
        self,
        user_id: int,
        start_hour: int,
        end_hour: int,
    ) -> bool:
        """Update user working hours."""
        if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
            return False
        if start_hour >= end_hour:
            return False
        
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.working_hours_start = start_hour
        user.working_hours_end = end_hour
        user.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        return True
    
    async def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user account."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        return True
    
    async def get_or_create_chat(
        self,
        telegram_chat_id: int,
        title: str,
        chat_type: str,
        description: Optional[str] = None,
    ) -> Chat:
        """Get existing chat or create new one."""
        # Try to find existing chat
        stmt = select(Chat).where(Chat.telegram_chat_id == telegram_chat_id)
        result = await self.db.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if chat:
            # Update chat information if provided
            if title:
                chat.title = title
            if description is not None:
                chat.description = description
            chat.updated_at = datetime.now(timezone.utc)
            await self.db.commit()
            return chat
        
        # Create new chat
        chat = Chat(
            telegram_chat_id=telegram_chat_id,
            title=title,
            type=chat_type,
            description=description,
            is_active=True,
        )
        
        self.db.add(chat)
        await self.db.commit()
        await self.db.refresh(chat)
        
        return chat
    
    async def get_chat_by_telegram_id(self, telegram_chat_id: int) -> Optional[Chat]:
        """Get chat by Telegram chat ID."""
        stmt = select(Chat).where(Chat.telegram_chat_id == telegram_chat_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def add_user_to_chat(
        self,
        user_id: int,
        chat_id: int,
        role: str = "member",
    ) -> bool:
        """Add user to chat with specified role."""
        # Check if membership already exists
        stmt = select(ChatMembership).where(
            and_(ChatMembership.user_id == user_id, ChatMembership.chat_id == chat_id)
        )
        result = await self.db.execute(stmt)
        membership = result.scalar_one_or_none()
        
        if membership:
            # Update existing membership
            membership.role = role
            membership.updated_at = datetime.now(timezone.utc)
        else:
            # Create new membership
            membership = ChatMembership(
                user_id=user_id,
                chat_id=chat_id,
                role=role,
                joined_at=datetime.now(timezone.utc),
            )
            self.db.add(membership)
        
        await self.db.commit()
        return True
    
    async def remove_user_from_chat(self, user_id: int, chat_id: int) -> bool:
        """Remove user from chat."""
        stmt = select(ChatMembership).where(
            and_(ChatMembership.user_id == user_id, ChatMembership.chat_id == chat_id)
        )
        result = await self.db.execute(stmt)
        membership = result.scalar_one_one_or_none()
        
        if membership:
            await self.db.delete(membership)
            await self.db.commit()
            return True
        
        return False
    
    async def get_chat_members(self, chat_id: int) -> List[User]:
        """Get all members of a chat."""
        stmt = (
            select(User)
            .join(ChatMembership, User.id == ChatMembership.user_id)
            .where(ChatMembership.chat_id == chat_id)
            .where(User.is_active == True)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_user_chats(self, user_id: int) -> List[Chat]:
        """Get all chats a user is member of."""
        stmt = (
            select(Chat)
            .join(ChatMembership, Chat.id == ChatMembership.chat_id)
            .where(ChatMembership.user_id == user_id)
            .where(Chat.is_active == True)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def validate_participants(
        self,
        participant_telegram_ids: List[int],
        chat_id: int,
    ) -> Dict[str, Any]:
        """Validate that participants are members of the chat."""
        # Get chat members
        chat_members = await self.get_chat_members(chat_id)
        chat_member_ids = {member.telegram_id for member in chat_members}
        
        # Check which participants are valid
        valid_participants = []
        invalid_participants = []
        
        for telegram_id in participant_telegram_ids:
            if telegram_id in chat_member_ids:
                # Find the user object
                user = next((m for m in chat_members if m.telegram_id == telegram_id), None)
                if user:
                    valid_participants.append(user)
            else:
                invalid_participants.append(telegram_id)
        
        return {
            "valid_participants": valid_participants,
            "invalid_participants": invalid_participants,
            "all_valid": len(invalid_participants) == 0,
        }
    
    async def get_active_users_count(self) -> int:
        """Get count of active users."""
        stmt = select(User).where(User.is_active == True)
        result = await self.db.execute(stmt)
        return len(result.scalars().all())
    
    async def get_active_chats_count(self) -> int:
        """Get count of active chats."""
        stmt = select(Chat).where(Chat.is_active == True)
        result = await self.db.execute(stmt)
        return len(result.scalars().all())


