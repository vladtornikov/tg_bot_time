"""Meeting-related models."""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base, TimestampMixin, SoftDeleteMixin


class MeetingState(enum.Enum):
    """Meeting state enumeration."""
    DRAFT = "draft"
    AWAITING_CONSENT = "awaiting_consent"
    RESOLVING = "resolving"
    VOTING = "voting"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELED = "canceled"


class ParticipantRole(enum.Enum):
    """Participant role enumeration."""
    REQUIRED = "required"
    OPTIONAL = "optional"


class Meeting(Base, TimestampMixin, SoftDeleteMixin):
    """Meeting model representing a scheduled meeting."""
    
    __tablename__ = "meetings"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign keys
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False, index=True)
    organizer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Meeting details
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Meeting state
    state: Mapped[MeetingState] = mapped_column(
        Enum(MeetingState),
        default=MeetingState.DRAFT,
        nullable=False,
        index=True,
    )
    
    # Selected time slot (set when confirmed)
    chosen_start_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    chosen_end_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Meeting metadata
    message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Telegram message ID
    calendar_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Google Calendar event ID
    
    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="meetings")
    organizer: Mapped["User"] = relationship("User", back_populates="organized_meetings")
    participants: Mapped[List["MeetingParticipant"]] = relationship(
        "MeetingParticipant",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )
    votes: Mapped[List["Vote"]] = relationship(
        "Vote",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )
    
    @property
    def is_active(self) -> bool:
        """Check if the meeting is in an active state."""
        return self.state in {
            MeetingState.DRAFT,
            MeetingState.AWAITING_CONSENT,
            MeetingState.RESOLVING,
            MeetingState.VOTING,
        }
    
    @property
    def is_completed(self) -> bool:
        """Check if the meeting is completed (confirmed or terminal state)."""
        return self.state in {
            MeetingState.CONFIRMED,
            MeetingState.FAILED,
            MeetingState.CANCELED,
        }
    
    def __repr__(self) -> str:
        return f"<Meeting(id={self.id}, topic='{self.topic}', state='{self.state.value}')>"


class MeetingParticipant(Base, TimestampMixin):
    """Meeting participant model representing user participation in a meeting."""
    
    __tablename__ = "meeting_participants"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign keys
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Participation details
    role: Mapped[ParticipantRole] = mapped_column(
        Enum(ParticipantRole),
        default=ParticipantRole.REQUIRED,
        nullable=False,
    )
    added_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.now(timezone.utc))
    
    # Relationships
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="participants")
    user: Mapped["User"] = relationship("User", back_populates="meeting_participations")
    
    def __repr__(self) -> str:
        return f"<MeetingParticipant(id={self.id}, meeting_id={self.meeting_id}, user_id={self.user_id}, role='{self.role.value}')>"
