"""OAuth-related models."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class OAuthToken(Base, TimestampMixin):
    """OAuth token model for storing encrypted calendar provider tokens."""
    
    __tablename__ = "oauth_tokens"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign key
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Provider information
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # google, yandex, etc.
    
    # Encrypted tokens (stored as base64 encoded encrypted data)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Token metadata
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[str] = mapped_column(Text, nullable=False)  # OAuth scopes granted
    
    # Token status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="oauth_tokens")
    
    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at
    
    @property
    def needs_refresh(self) -> bool:
        """Check if the token needs refresh (expires within 5 minutes)."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= (self.expires_at - datetime.timedelta(minutes=5))
    
    def __repr__(self) -> str:
        return f"<OAuthToken(id={self.id}, user_id={self.user_id}, provider='{self.provider}')>"
