"""Integration tests for Meeting endpoints."""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient


class TestMeetingEndpoints:
    """Test Meeting API endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_meeting_success(self, test_client: AsyncClient, test_user, test_chat):
        """Test creating meeting successfully."""
        meeting_data = {
            "title": "Test Meeting",
            "description": "Test meeting description",
            "creator_id": test_user.id,
            "chat_id": test_chat.id,
            "duration_minutes": 60,
            "earliest_start": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "latest_end": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "working_hours_start": 9,
            "working_hours_end": 17,
            "timezone": "UTC",
            "participants": [
                {
                    "telegram_id": test_user.telegram_id,
                    "username": test_user.username
                }
            ]
        }
        
        response = await test_client.post("/meetings", json=meeting_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "meeting_id" in data
        assert data["meeting_data"]["title"] == "Test Meeting"
        assert data["meeting_data"]["status"] == "created"
    
    @pytest.mark.asyncio
    async def test_create_meeting_invalid_data(self, test_client: AsyncClient):
        """Test creating meeting with invalid data."""
        meeting_data = {
            "title": "",  # Invalid: empty title
            "creator_id": 99999,  # Invalid: non-existent user
            "duration_minutes": 0,  # Invalid: zero duration
        }
        
        response = await test_client.post("/meetings", json=meeting_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_create_meeting_missing_required_fields(self, test_client: AsyncClient):
        """Test creating meeting with missing required fields."""
        meeting_data = {
            "title": "Test Meeting",
            # Missing creator_id, duration_minutes, etc.
        }
        
        response = await test_client.post("/meetings", json=meeting_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_get_meeting_success(self, test_client: AsyncClient, test_meeting):
        """Test getting meeting successfully."""
        response = await test_client.get(f"/meetings/{test_meeting.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["meeting_data"]["id"] == test_meeting.id
        assert data["meeting_data"]["title"] == test_meeting.title
        assert "participants" in data["meeting_data"]
    
    @pytest.mark.asyncio
    async def test_get_meeting_not_found(self, test_client: AsyncClient):
        """Test getting non-existent meeting."""
        response = await test_client.get("/meetings/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_resolve_meeting_time_slots_success(self, test_client: AsyncClient, test_meeting, test_meeting_participant):
        """Test resolving meeting time slots successfully."""
        response = await test_client.post(f"/meetings/{test_meeting.id}/resolve")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "time_slots" in data
        assert "meeting_id" in data
    
    @pytest.mark.asyncio
    async def test_resolve_meeting_time_slots_not_found(self, test_client: AsyncClient):
        """Test resolving time slots for non-existent meeting."""
        response = await test_client.post("/meetings/99999/resolve")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_resolve_meeting_time_slots_no_participants(self, test_client: AsyncClient, test_meeting):
        """Test resolving time slots for meeting with no participants."""
        response = await test_client.post(f"/meetings/{test_meeting.id}/resolve")
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "No active participants" in data["error"]
    
    @pytest.mark.asyncio
    async def test_confirm_meeting_success(self, test_client: AsyncClient, test_meeting):
        """Test confirming meeting successfully."""
        confirm_data = {
            "start_time": (datetime.utcnow() + timedelta(days=1, hours=10)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(days=1, hours=11)).isoformat(),
        }
        
        response = await test_client.post(
            f"/meetings/{test_meeting.id}/confirm",
            json=confirm_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "meeting_id" in data
        assert "event_id" in data
    
    @pytest.mark.asyncio
    async def test_confirm_meeting_not_found(self, test_client: AsyncClient):
        """Test confirming non-existent meeting."""
        confirm_data = {
            "start_time": (datetime.utcnow() + timedelta(days=1, hours=10)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(days=1, hours=11)).isoformat(),
        }
        
        response = await test_client.post(
            "/meetings/99999/confirm",
            json=confirm_data
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_confirm_meeting_invalid_time(self, test_client: AsyncClient, test_meeting):
        """Test confirming meeting with invalid time."""
        confirm_data = {
            "start_time": (datetime.utcnow() - timedelta(days=1)).isoformat(),  # Past time
            "end_time": (datetime.utcnow() - timedelta(days=1, hours=1)).isoformat(),
        }
        
        response = await test_client.post(
            f"/meetings/{test_meeting.id}/confirm",
            json=confirm_data
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_vote_on_time_slot_success(self, test_client: AsyncClient, test_meeting_participant):
        """Test voting on time slot successfully."""
        vote_data = {
            "participant_id": test_meeting_participant.id,
            "start_time": (datetime.utcnow() + timedelta(days=1, hours=10)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(days=1, hours=11)).isoformat(),
            "preference": "available",
        }
        
        response = await test_client.post(
            f"/meetings/{test_meeting_participant.meeting_id}/vote",
            json=vote_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "vote_id" in data
        assert data["vote_data"]["preference"] == "available"
    
    @pytest.mark.asyncio
    async def test_vote_on_time_slot_meeting_not_found(self, test_client: AsyncClient):
        """Test voting on time slot for non-existent meeting."""
        vote_data = {
            "participant_id": 1,
            "start_time": (datetime.utcnow() + timedelta(days=1, hours=10)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(days=1, hours=11)).isoformat(),
            "preference": "available",
        }
        
        response = await test_client.post(
            "/meetings/99999/vote",
            json=vote_data
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_vote_on_time_slot_invalid_preference(self, test_client: AsyncClient, test_meeting_participant):
        """Test voting on time slot with invalid preference."""
        vote_data = {
            "participant_id": test_meeting_participant.id,
            "start_time": (datetime.utcnow() + timedelta(days=1, hours=10)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(days=1, hours=11)).isoformat(),
            "preference": "invalid_preference",
        }
        
        response = await test_client.post(
            f"/meetings/{test_meeting_participant.meeting_id}/vote",
            json=vote_data
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_get_meeting_votes_success(self, test_client: AsyncClient, test_meeting, test_vote):
        """Test getting meeting votes successfully."""
        response = await test_client.get(f"/meetings/{test_meeting.id}/votes")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "votes" in data
        assert "meeting_id" in data
        assert len(data["votes"]) >= 1  # At least the test vote
    
    @pytest.mark.asyncio
    async def test_get_meeting_votes_not_found(self, test_client: AsyncClient):
        """Test getting votes for non-existent meeting."""
        response = await test_client.get("/meetings/99999/votes")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_cancel_meeting_success(self, test_client: AsyncClient, test_meeting):
        """Test cancelling meeting successfully."""
        response = await test_client.delete(f"/meetings/{test_meeting.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_cancel_meeting_not_found(self, test_client: AsyncClient):
        """Test cancelling non-existent meeting."""
        response = await test_client.delete("/meetings/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_get_user_meetings_success(self, test_client: AsyncClient, test_user, test_meeting):
        """Test getting user meetings successfully."""
        response = await test_client.get(f"/meetings/user/{test_user.telegram_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "meetings" in data
        assert "user_id" in data
        assert len(data["meetings"]) >= 1  # At least the test meeting
    
    @pytest.mark.asyncio
    async def test_get_user_meetings_not_found(self, test_client: AsyncClient):
        """Test getting meetings for non-existent user."""
        response = await test_client.get("/meetings/user/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_get_user_meetings_empty(self, test_client: AsyncClient):
        """Test getting meetings for user with no meetings."""
        # Create user without meetings
        from src.models.user import User
        from src.database.session import get_db_session
        
        async with get_db_session() as session:
            user = User(
                telegram_id=88888,
                username="lonelyuser",
                first_name="Lonely",
                last_name="User",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            response = await test_client.get(f"/meetings/user/{user.telegram_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "meetings" in data
            assert len(data["meetings"]) == 0
    
    @pytest.mark.asyncio
    async def test_create_meeting_with_multiple_participants(self, test_client: AsyncClient, test_user, test_chat):
        """Test creating meeting with multiple participants."""
        # Create additional users
        from src.models.user import User
        from src.database.session import get_db_session
        
        async with get_db_session() as session:
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
            session.add_all([user1, user2])
            await session.commit()
            await session.refresh(user1)
            await session.refresh(user2)
            
            meeting_data = {
                "title": "Multi-participant Meeting",
                "description": "Meeting with multiple participants",
                "creator_id": test_user.id,
                "chat_id": test_chat.id,
                "duration_minutes": 60,
                "earliest_start": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "latest_end": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                "working_hours_start": 9,
                "working_hours_end": 17,
                "timezone": "UTC",
                "participants": [
                    {
                        "telegram_id": test_user.telegram_id,
                        "username": test_user.username
                    },
                    {
                        "telegram_id": user1.telegram_id,
                        "username": user1.username
                    },
                    {
                        "telegram_id": user2.telegram_id,
                        "username": user2.username
                    }
                ]
            }
            
            response = await test_client.post("/meetings", json=meeting_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert "meeting_id" in data
            assert len(data["meeting_data"]["participants"]) == 3
