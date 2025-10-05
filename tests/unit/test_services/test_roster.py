"""Unit tests for Roster service."""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.roster import RosterService


class TestRosterService:
    """Test RosterService."""
    
    @pytest.fixture
    def roster_service(self):
        """Create RosterService instance."""
        return RosterService()
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, roster_service, test_session):
        """Test registering user successfully."""
        user_data = {
            "telegram_id": 98765,
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "language_code": "en",
        }
        
        result = await roster_service.register_user(
            user_data, session=test_session
        )
        
        assert result["success"] is True
        assert "user_id" in result
        assert result["user_data"]["telegram_id"] == 98765
        assert result["user_data"]["username"] == "newuser"
    
    @pytest.mark.asyncio
    async def test_register_user_already_exists(self, roster_service, test_session, test_user):
        """Test registering user that already exists."""
        user_data = {
            "telegram_id": test_user.telegram_id,  # Same as existing user
            "username": "updateduser",
            "first_name": "Updated",
            "last_name": "User",
            "language_code": "en",
        }
        
        result = await roster_service.register_user(
            user_data, session=test_session
        )
        
        assert result["success"] is True
        assert result["user_id"] == test_user.id
        # Should update existing user
        assert result["user_data"]["username"] == "updateduser"
        assert result["user_data"]["first_name"] == "Updated"
    
    @pytest.mark.asyncio
    async def test_register_user_invalid_data(self, roster_service, test_session):
        """Test registering user with invalid data."""
        user_data = {
            "telegram_id": None,  # Invalid
            "username": "invaliduser",
        }
        
        result = await roster_service.register_user(
            user_data, session=test_session
        )
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_success(self, roster_service, test_session, test_user):
        """Test getting user by Telegram ID successfully."""
        result = await roster_service.get_user_by_telegram_id(
            test_user.telegram_id, session=test_session
        )
        
        assert result["success"] is True
        assert result["user_data"]["id"] == test_user.id
        assert result["user_data"]["telegram_id"] == test_user.telegram_id
        assert result["user_data"]["username"] == test_user.username
    
    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_not_found(self, roster_service, test_session):
        """Test getting user by Telegram ID when not found."""
        result = await roster_service.get_user_by_telegram_id(
            99999, session=test_session  # Non-existent Telegram ID
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "User not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, roster_service, test_session, test_user):
        """Test getting user by ID successfully."""
        result = await roster_service.get_user_by_id(
            test_user.id, session=test_session
        )
        
        assert result["success"] is True
        assert result["user_data"]["id"] == test_user.id
        assert result["user_data"]["telegram_id"] == test_user.telegram_id
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, roster_service, test_session):
        """Test getting user by ID when not found."""
        result = await roster_service.get_user_by_id(
            99999, session=test_session  # Non-existent ID
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "User not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_update_user_success(self, roster_service, test_session, test_user):
        """Test updating user successfully."""
        update_data = {
            "username": "updateduser",
            "first_name": "Updated",
            "last_name": "User",
        }
        
        result = await roster_service.update_user(
            test_user.id, update_data, session=test_session
        )
        
        assert result["success"] is True
        assert result["user_data"]["username"] == "updateduser"
        assert result["user_data"]["first_name"] == "Updated"
        assert result["user_data"]["last_name"] == "User"
    
    @pytest.mark.asyncio
    async def test_update_user_not_found(self, roster_service, test_session):
        """Test updating user that doesn't exist."""
        update_data = {"username": "updateduser"}
        
        result = await roster_service.update_user(
            99999, update_data, session=test_session  # Non-existent ID
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "User not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_add_user_to_chat_success(self, roster_service, test_session, test_user, test_chat):
        """Test adding user to chat successfully."""
        result = await roster_service.add_user_to_chat(
            test_user.id, test_chat.id, session=test_session
        )
        
        assert result["success"] is True
        assert result["membership_data"]["user_id"] == test_user.id
        assert result["membership_data"]["chat_id"] == test_chat.id
        assert result["membership_data"]["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_add_user_to_chat_already_member(self, roster_service, test_session, test_chat_membership):
        """Test adding user to chat when already a member."""
        result = await roster_service.add_user_to_chat(
            test_chat_membership.user_id, 
            test_chat_membership.chat_id, 
            session=test_session
        )
        
        assert result["success"] is True
        assert result["membership_data"]["id"] == test_chat_membership.id
        # Status should remain unchanged
        assert result["membership_data"]["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_remove_user_from_chat_success(self, roster_service, test_session, test_chat_membership):
        """Test removing user from chat successfully."""
        result = await roster_service.remove_user_from_chat(
            test_chat_membership.user_id,
            test_chat_membership.chat_id,
            session=test_session
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_remove_user_from_chat_not_member(self, roster_service, test_session, test_user, test_chat):
        """Test removing user from chat when not a member."""
        result = await roster_service.remove_user_from_chat(
            test_user.id, test_chat.id, session=test_session
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "not a member" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_chat_members_success(self, roster_service, test_session, test_chat, test_chat_membership):
        """Test getting chat members successfully."""
        result = await roster_service.get_chat_members(
            test_chat.id, session=test_session
        )
        
        assert result["success"] is True
        assert len(result["members"]) == 1
        assert result["members"][0]["user_id"] == test_chat_membership.user_id
        assert result["members"][0]["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_get_chat_members_empty(self, roster_service, test_session, test_chat):
        """Test getting chat members when chat is empty."""
        result = await roster_service.get_chat_members(
            test_chat.id, session=test_session
        )
        
        assert result["success"] is True
        assert len(result["members"]) == 0
    
    @pytest.mark.asyncio
    async def test_get_user_chats_success(self, roster_service, test_session, test_user, test_chat_membership):
        """Test getting user chats successfully."""
        result = await roster_service.get_user_chats(
            test_user.id, session=test_session
        )
        
        assert result["success"] is True
        assert len(result["chats"]) == 1
        assert result["chats"][0]["chat_id"] == test_chat_membership.chat_id
        assert result["chats"][0]["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_get_user_chats_empty(self, roster_service, test_session):
        """Test getting user chats when user has no chats."""
        # Create user without chat memberships
        from src.models.user import User
        
        user = User(
            telegram_id=99999,
            username="lonelyuser",
            first_name="Lonely",
            last_name="User",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        
        result = await roster_service.get_user_chats(
            user.id, session=test_session
        )
        
        assert result["success"] is True
        assert len(result["chats"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_participants_success(self, roster_service, test_session, test_user):
        """Test validating participants successfully."""
        participants = [
            {"telegram_id": test_user.telegram_id, "username": test_user.username},
            {"telegram_id": 11111, "username": "user1"},
            {"telegram_id": 22222, "username": "user2"},
        ]
        
        result = await roster_service.validate_participants(
            participants, session=test_session
        )
        
        assert result["success"] is True
        assert len(result["valid_participants"]) == 1  # Only test_user exists
        assert len(result["invalid_participants"]) == 2  # user1 and user2 don't exist
        assert result["valid_participants"][0]["telegram_id"] == test_user.telegram_id
    
    @pytest.mark.asyncio
    async def test_validate_participants_all_valid(self, roster_service, test_session):
        """Test validating participants when all are valid."""
        # Create additional users
        from src.models.user import User
        
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
        
        participants = [
            {"telegram_id": user1.telegram_id, "username": user1.username},
            {"telegram_id": user2.telegram_id, "username": user2.username},
        ]
        
        result = await roster_service.validate_participants(
            participants, session=test_session
        )
        
        assert result["success"] is True
        assert len(result["valid_participants"]) == 2
        assert len(result["invalid_participants"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_participants_empty_list(self, roster_service, test_session):
        """Test validating empty participants list."""
        result = await roster_service.validate_participants(
            [], session=test_session
        )
        
        assert result["success"] is True
        assert len(result["valid_participants"]) == 0
        assert len(result["invalid_participants"]) == 0
    
    @pytest.mark.asyncio
    async def test_update_user_last_active(self, roster_service, test_session, test_user):
        """Test updating user last active timestamp."""
        from datetime import datetime
        
        original_last_active = test_user.last_active_at
        
        result = await roster_service.update_user_last_active(
            test_user.id, session=test_session
        )
        
        assert result["success"] is True
        
        # Verify the timestamp was updated
        await test_session.refresh(test_user)
        assert test_user.last_active_at > original_last_active
    
    @pytest.mark.asyncio
    async def test_update_user_last_active_not_found(self, roster_service, test_session):
        """Test updating last active for non-existent user."""
        result = await roster_service.update_user_last_active(
            99999, session=test_session  # Non-existent ID
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "User not found" in result["error"]
