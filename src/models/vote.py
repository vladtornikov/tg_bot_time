"""Vote-related models."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base, TimestampMixin


class VoteType(enum.Enum):
    """Vote type enumeration."""
    YES = "yes"
    NO = "no"
    MAYBE = "maybe"


class Vote(Base, TimestampMixin):
    """Vote model representing a user's vote for a specific time slot."""
    
    __tablename__ = "votes"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign keys
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Vote details
    slot_start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    slot_end_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vote: Mapped[VoteType] = mapped_column(Enum(VoteType), nullable=False)
    voted_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.now(timezone.utc))
    
    # Vote metadata
    comment: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Relationships
    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="votes")
    user: Mapped["User"] = relationship("User", back_populates="votes")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "meeting_id",
            "user_id",
            "slot_start_utc",
            name="uq_vote_user_slot",
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Vote(id={self.id}, meeting_id={self.meeting_id}, user_id={self.user_id}, vote='{self.vote.value}')>"


