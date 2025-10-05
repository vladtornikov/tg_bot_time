"""Unit tests for User model."""

import pytest
from datetime import datetime, timedelta

from src.models.user import User, Chat, ChatMembership


class TestUser:
    """Test User model."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, test_session):
        """Test creating a user."""
        user = User(
            telegram_id=12345,
            username="testuser",
            first_name="Test",
            last_name="User",
            language_code="en",
        )
        
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        
        assert user.id is not None
        assert user.telegram_id == 12345
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.language_code == "en"
        assert user.created_at is not None
        assert user.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_user_full_name(self, test_user):
        """Test user full name property."""
        assert test_user.full_name == "Test User"
        
        # Test with only first name
        test_user.last_name = None
        assert test_user.full_name == "Test"
        
        # Test with only last name
        test_user.first_name = None
        test_user.last_name = "User"
        assert test_user.full_name == "User"
    
    @pytest.mark.asyncio
    async def test_user_str_representation(self, test_user):
        """Test user string representation."""
        assert str(test_user) == "Test User (@testuser)"
        
        # Test without username
        test_user.username = None
        assert str(test_user) == "Test User"
    
    @pytest.mark.asyncio
    async def test_user_soft_delete(self, test_session, test_user):
        """Test user soft delete."""
        user_id = test_user.id
        
        # Soft delete the user
        test_user.deleted_at = datetime.utcnow()
        await test_session.commit()
        
        # Verify user is soft deleted
        assert test_user.deleted_at is not None
        assert test_user.is_deleted is True


class TestChat:
    """Test Chat model."""
    
    @pytest.mark.asyncio
    async def test_create_chat(self, test_session):
        """Test creating a chat."""
        chat = Chat(
            telegram_id=-1001234567890,
            title="Test Group",
            chat_type="group",
        )
        
        test_session.add(chat)
        await test_session.commit()
        await test_session.refresh(chat)
        
        assert chat.id is not None
        assert chat.telegram_id == -1001234567890
        assert chat.title == "Test Group"
        assert chat.chat_type == "group"
        assert chat.created_at is not None
        assert chat.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_chat_str_representation(self, test_chat):
        """Test chat string representation."""
        assert str(test_chat) == "Test Group (group)"
        
        # Test without title
        test_chat.title = None
        assert str(test_chat) == "Unknown (group)"


class TestChatMembership:
    """Test ChatMembership model."""
    
    @pytest.mark.asyncio
    async def test_create_chat_membership(self, test_session, test_user, test_chat):
        """Test creating a chat membership."""
        membership = ChatMembership(
            user_id=test_user.id,
            chat_id=test_chat.id,
            status="active",
        )
        
        test_session.add(membership)
        await test_session.commit()
        await test_session.refresh(membership)
        
        assert membership.id is not None
        assert membership.user_id == test_user.id
        assert membership.chat_id == test_chat.id
        assert membership.status == "active"
        assert membership.created_at is not None
        assert membership.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_chat_membership_relationships(self, test_session, test_chat_membership):
        """Test chat membership relationships."""
        await test_session.refresh(test_chat_membership, ["user", "chat"])
        
        assert test_chat_membership.user is not None
        assert test_chat_membership.chat is not None
        assert test_chat_membership.user.username == "testuser"
        assert test_chat_membership.chat.title == "Test Group"
    
    @pytest.mark.asyncio
    async def test_chat_membership_status_validation(self, test_session, test_user, test_chat):
        """Test chat membership status validation."""
        # Valid statuses
        valid_statuses = ["active", "inactive", "banned", "left"]
        
        for status in valid_statuses:
            membership = ChatMembership(
                user_id=test_user.id,
                chat_id=test_chat.id,
                status=status,
            )
            test_session.add(membership)
            await test_session.commit()
            await test_session.refresh(membership)
            assert membership.status == status
            await test_session.delete(membership)
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_chat_membership_soft_delete(self, test_session, test_chat_membership):
        """Test chat membership soft delete."""
        membership_id = test_chat_membership.id
        
        # Soft delete the membership
        test_chat_membership.deleted_at = datetime.utcnow()
        await test_session.commit()
        
        # Verify membership is soft deleted
        assert test_chat_membership.deleted_at is not None
        assert test_chat_membership.is_deleted is True


class TestModelRelationships:
    """Test model relationships."""
    
    @pytest.mark.asyncio
    async def test_user_chat_memberships_relationship(self, test_session, test_user):
        """Test user-chat memberships relationship."""
        # Create additional chats and memberships
        chat1 = Chat(
            telegram_id=-1001111111111,
            title="Chat 1",
            chat_type="group",
        )
        chat2 = Chat(
            telegram_id=-1002222222222,
            title="Chat 2",
            chat_type="supergroup",
        )
        
        test_session.add_all([chat1, chat2])
        await test_session.commit()
        
        membership1 = ChatMembership(
            user_id=test_user.id,
            chat_id=chat1.id,
            status="active",
        )
        membership2 = ChatMembership(
            user_id=test_user.id,
            chat_id=chat2.id,
            status="active",
        )
        
        test_session.add_all([membership1, membership2])
        await test_session.commit()
        
        # Refresh user with memberships
        await test_session.refresh(test_user, ["chat_memberships"])
        
        assert len(test_user.chat_memberships) == 3  # Including the one from fixture
        assert all(m.status == "active" for m in test_user.chat_memberships)
    
    @pytest.mark.asyncio
    async def test_chat_members_relationship(self, test_session, test_chat):
        """Test chat-members relationship."""
        # Create additional users and memberships
        user1 = User(
            telegram_id=11111,
            username="user1",
            first_name="User",
            last_name="One",
        )
        user2 = User(
            telegram_id=22222,
            username="user2",
            first_name="User",
            last_name="Two",
        )
        
        test_session.add_all([user1, user2])
        await test_session.commit()
        
        membership1 = ChatMembership(
            user_id=user1.id,
            chat_id=test_chat.id,
            status="active",
        )
        membership2 = ChatMembership(
            user_id=user2.id,
            chat_id=test_chat.id,
            status="active",
        )
        
        test_session.add_all([membership1, membership2])
        await test_session.commit()
        
        # Refresh chat with memberships
        await test_session.refresh(test_chat, ["memberships"])
        
        assert len(test_chat.memberships) == 3  # Including the one from fixture
        assert all(m.status == "active" for m in test_chat.memberships)
