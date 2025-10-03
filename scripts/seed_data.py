#!/usr/bin/env python3
"""
Seed the database with test data for development.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.session import get_session
from models.user import User, Chat, ChatMembership
from models.oauth import OAuthToken
from sqlalchemy.ext.asyncio import AsyncSession


async def seed_data():
    """Seed the database with test data."""
    async with get_session() as session:
        # Create test users
        users = [
            User(
                telegram_id=123456789,
                username="testuser1",
                first_name="Test",
                last_name="User 1",
                timezone="UTC",
                working_hours_start=8,
                working_hours_end=20,
            ),
            User(
                telegram_id=987654321,
                username="testuser2",
                first_name="Test",
                last_name="User 2",
                timezone="UTC",
                working_hours_start=9,
                working_hours_end=17,
            ),
        ]
        
        for user in users:
            session.add(user)
        
        await session.commit()
        
        # Create test chat
        chat = Chat(
            telegram_chat_id=-1001234567890,
            title="Test Chat",
            type="supergroup",
        )
        session.add(chat)
        await session.commit()
        
        # Create chat memberships
        for user in users:
            membership = ChatMembership(
                chat_id=chat.id,
                user_id=user.id,
                role="member",
                joined_at=datetime.now(timezone.utc),
            )
            session.add(membership)
        
        await session.commit()
        
        print("Test data seeded successfully")


if __name__ == "__main__":
    asyncio.run(seed_data())
