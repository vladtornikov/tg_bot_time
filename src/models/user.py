"""User-related models."""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import BigInteger, String, Integer, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, SoftDeleteMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    """User model representing a Telegram user."""
    
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Telegram-specific fields
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # User preferences
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    working_hours_start: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    working_hours_end: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    
    # User status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    oauth_tokens: Mapped[List["OAuthToken"]] = relationship(
        "OAuthToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    organized_meetings: Mapped[List["Meeting"]] = relationship(
        "Meeting",
        back_populates="organizer",
        foreign_keys="Meeting.organizer_id",
    )
    meeting_participations: Mapped[List["MeetingParticipant"]] = relationship(
        "MeetingParticipant",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    votes: Mapped[List["Vote"]] = relationship(
        "Vote",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    chat_memberships: Mapped[List["ChatMembership"]] = relationship(
        "ChatMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username='{self.username}')>"


class Chat(Base, TimestampMixin):
    """Chat model representing a Telegram chat/group."""
    
    __tablename__ = "chats"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Telegram-specific fields
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # group, supergroup, channel
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Chat status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    meetings: Mapped[List["Meeting"]] = relationship(
        "Meeting",
        back_populates="chat",
    )
    memberships: Mapped[List["ChatMembership"]] = relationship(
        "ChatMembership",
        back_populates="chat",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Chat(id={self.id}, telegram_chat_id={self.telegram_chat_id}, title='{self.title}')>"


class ChatMembership(Base, TimestampMixin):
    """Chat membership model representing user membership in a chat."""
    
    __tablename__ = "chat_memberships"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign keys
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Membership details
    role: Mapped[str] = mapped_column(String(50), default="member", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.now(timezone.utc))
    
    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="memberships")
    user: Mapped["User"] = relationship("User", back_populates="chat_memberships")
    
    def __repr__(self) -> str:
        return f"<ChatMembership(id={self.id}, chat_id={self.chat_id}, user_id={self.user_id}, role='{self.role}')>"
