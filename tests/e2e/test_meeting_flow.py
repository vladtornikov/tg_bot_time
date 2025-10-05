"""End-to-end tests for complete meeting flow."""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


class TestMeetingFlow:
    """Test complete meeting scheduling flow."""
    
    @pytest.mark.asyncio
    async def test_complete_meeting_flow(self, test_client: AsyncClient, test_user, test_chat):
        """Test complete meeting scheduling flow from creation to confirmation."""
        
        # Step 1: Create a meeting
        meeting_data = {
            "title": "E2E Test Meeting",
            "description": "End-to-end test meeting",
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
        
        # Create meeting
        create_response = await test_client.post("/meetings", json=meeting_data)
        assert create_response.status_code == 201
        create_data = create_response.json()
        assert create_data["success"] is True
        meeting_id = create_data["meeting_id"]
        
        # Step 2: Get meeting details
        get_response = await test_client.get(f"/meetings/{meeting_id}")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["success"] is True
        assert get_data["meeting_data"]["title"] == "E2E Test Meeting"
        assert get_data["meeting_data"]["status"] == "created"
        
        # Step 3: Resolve time slots (mock Google Calendar)
        with patch('src.services.scheduler.GoogleCalendarProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.get_free_busy_times.return_value = {
                "success": True,
                "free_busy_times": [
                    {
                        "start": (datetime.utcnow() + timedelta(days=1, hours=10)).isoformat(),
                        "end": (datetime.utcnow() + timedelta(days=1, hours=11)).isoformat(),
                        "available": True,
                    },
                    {
                        "start": (datetime.utcnow() + timedelta(days=1, hours=14)).isoformat(),
                        "end": (datetime.utcnow() + timedelta(days=1, hours=15)).isoformat(),
                        "available": True,
                    },
                    {
                        "start": (datetime.utcnow() + timedelta(days=1, hours=16)).isoformat(),
                        "end": (datetime.utcnow() + timedelta(days=1, hours=17)).isoformat(),
                        "available": False,
                    },
                ]
            }
            
            resolve_response = await test_client.post(f"/meetings/{meeting_id}/resolve")
            assert resolve_response.status_code == 200
            resolve_data = resolve_response.json()
            assert resolve_data["success"] is True
            assert "time_slots" in resolve_data
            assert len(resolve_data["time_slots"]) == 2  # Only available slots
        
        # Step 4: Vote on time slots
        time_slots = resolve_data["time_slots"]
        first_slot = time_slots[0]
        
        # Get meeting participants
        meeting_response = await test_client.get(f"/meetings/{meeting_id}")
        meeting_data = meeting_response.json()
        participant = meeting_data["meeting_data"]["participants"][0]
        
        vote_data = {
            "participant_id": participant["id"],
            "start_time": first_slot["start"],
            "end_time": first_slot["end"],
            "preference": "available",
        }
        
        vote_response = await test_client.post(f"/meetings/{meeting_id}/vote", json=vote_data)
        assert vote_response.status_code == 200
        vote_result = vote_response.json()
        assert vote_result["success"] is True
        
        # Step 5: Get voting results
        votes_response = await test_client.get(f"/meetings/{meeting_id}/votes")
        assert votes_response.status_code == 200
        votes_data = votes_response.json()
        assert votes_data["success"] is True
        assert len(votes_data["votes"]) >= 1
        
        # Step 6: Confirm meeting (mock Google Calendar event creation)
        with patch('src.services.scheduler.GoogleCalendarProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.create_calendar_event.return_value = {
                "success": True,
                "event_id": "test_event_123",
            }
            
            confirm_data = {
                "start_time": first_slot["start"],
                "end_time": first_slot["end"],
            }
            
            confirm_response = await test_client.post(
                f"/meetings/{meeting_id}/confirm",
                json=confirm_data
            )
            assert confirm_response.status_code == 200
            confirm_result = confirm_response.json()
            assert confirm_result["success"] is True
            assert "event_id" in confirm_result
        
        # Step 7: Verify meeting status is confirmed
        final_response = await test_client.get(f"/meetings/{meeting_id}")
        assert final_response.status_code == 200
        final_data = final_response.json()
        assert final_data["success"] is True
        assert final_data["meeting_data"]["status"] == "confirmed"
    
    @pytest.mark.asyncio
    async def test_meeting_flow_with_oauth_integration(self, test_client: AsyncClient, test_user, test_chat):
        """Test meeting flow with OAuth integration."""
        
        # Step 1: Start OAuth flow
        oauth_start_response = await test_client.get("/oauth/google/start")
        assert oauth_start_response.status_code == 200
        oauth_start_data = oauth_start_response.json()
        assert oauth_start_data["success"] is True
        assert "oauth_url" in oauth_start_data
        
        # Step 2: Simulate OAuth callback
        state = oauth_start_data["state"]
        oauth_callback_response = await test_client.get(
            f"/oauth/google/callback?code=test_auth_code&state={state}"
        )
        assert oauth_callback_response.status_code == 200
        oauth_callback_data = oauth_callback_response.json()
        assert oauth_callback_data["success"] is True
        
        # Step 3: Check OAuth status
        oauth_status_response = await test_client.get(f"/oauth/google/status?user_id={test_user.id}")
        assert oauth_status_response.status_code == 200
        oauth_status_data = oauth_status_response.json()
        assert oauth_status_data["success"] is True
        assert oauth_status_data["provider"] == "google"
        
        # Step 4: Create meeting
        meeting_data = {
            "title": "OAuth Test Meeting",
            "description": "Meeting with OAuth integration",
            "creator_id": test_user.id,
            "chat_id": test_chat.id,
            "duration_minutes": 30,
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
        
        create_response = await test_client.post("/meetings", json=meeting_data)
        assert create_response.status_code == 201
        create_data = create_response.json()
        meeting_id = create_data["meeting_id"]
        
        # Step 5: Resolve time slots (with OAuth token)
        with patch('src.services.scheduler.GoogleCalendarProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.get_free_busy_times.return_value = {
                "success": True,
                "free_busy_times": [
                    {
                        "start": (datetime.utcnow() + timedelta(days=1, hours=10)).isoformat(),
                        "end": (datetime.utcnow() + timedelta(days=1, hours=10, minutes=30)).isoformat(),
                        "available": True,
                    }
                ]
            }
            
            resolve_response = await test_client.post(f"/meetings/{meeting_id}/resolve")
            assert resolve_response.status_code == 200
            resolve_data = resolve_response.json()
            assert resolve_data["success"] is True
    
    @pytest.mark.asyncio
    async def test_meeting_flow_with_multiple_participants(self, test_client: AsyncClient, test_user, test_chat):
        """Test meeting flow with multiple participants."""
        
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
            
            # Create meeting with multiple participants
            meeting_data = {
                "title": "Multi-participant E2E Test",
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
            
            # Create meeting
            create_response = await test_client.post("/meetings", json=meeting_data)
            assert create_response.status_code == 201
            create_data = create_response.json()
            meeting_id = create_data["meeting_id"]
            
            # Verify meeting has 3 participants
            get_response = await test_client.get(f"/meetings/{meeting_id}")
            assert get_response.status_code == 200
            get_data = get_response.json()
            assert len(get_data["meeting_data"]["participants"]) == 3
            
            # Resolve time slots
            with patch('src.services.scheduler.GoogleCalendarProvider') as mock_provider_class:
                mock_provider = AsyncMock()
                mock_provider_class.return_value = mock_provider
                mock_provider.get_free_busy_times.return_value = {
                    "success": True,
                    "free_busy_times": [
                        {
                            "start": (datetime.utcnow() + timedelta(days=1, hours=10)).isoformat(),
                            "end": (datetime.utcnow() + timedelta(days=1, hours=11)).isoformat(),
                            "available": True,
                        }
                    ]
                }
                
                resolve_response = await test_client.post(f"/meetings/{meeting_id}/resolve")
                assert resolve_response.status_code == 200
                resolve_data = resolve_response.json()
                assert resolve_data["success"] is True
    
    @pytest.mark.asyncio
    async def test_meeting_flow_error_scenarios(self, test_client: AsyncClient, test_user, test_chat):
        """Test meeting flow error scenarios."""
        
        # Test 1: Create meeting with invalid data
        invalid_meeting_data = {
            "title": "",  # Empty title
            "creator_id": test_user.id,
            "chat_id": test_chat.id,
            "duration_minutes": 0,  # Invalid duration
        }
        
        create_response = await test_client.post("/meetings", json=invalid_meeting_data)
        assert create_response.status_code == 422
        
        # Test 2: Create meeting with non-existent user
        non_existent_meeting_data = {
            "title": "Test Meeting",
            "creator_id": 99999,  # Non-existent user
            "chat_id": test_chat.id,
            "duration_minutes": 60,
            "earliest_start": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "latest_end": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "working_hours_start": 9,
            "working_hours_end": 17,
            "timezone": "UTC",
            "participants": [],
        }
        
        create_response = await test_client.post("/meetings", json=non_existent_meeting_data)
        assert create_response.status_code == 422
        
        # Test 3: Get non-existent meeting
        get_response = await test_client.get("/meetings/99999")
        assert get_response.status_code == 404
        
        # Test 4: Resolve time slots for non-existent meeting
        resolve_response = await test_client.post("/meetings/99999/resolve")
        assert resolve_response.status_code == 404
        
        # Test 5: Vote on non-existent meeting
        vote_data = {
            "participant_id": 1,
            "start_time": (datetime.utcnow() + timedelta(days=1, hours=10)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(days=1, hours=11)).isoformat(),
            "preference": "available",
        }
        
        vote_response = await test_client.post("/meetings/99999/vote", json=vote_data)
        assert vote_response.status_code == 404
        
        # Test 6: Confirm non-existent meeting
        confirm_data = {
            "start_time": (datetime.utcnow() + timedelta(days=1, hours=10)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(days=1, hours=11)).isoformat(),
        }
        
        confirm_response = await test_client.post("/meetings/99999/confirm", json=confirm_data)
        assert confirm_response.status_code == 404
        
        # Test 7: Cancel non-existent meeting
        cancel_response = await test_client.delete("/meetings/99999")
        assert cancel_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_meeting_flow_with_voting(self, test_client: AsyncClient, test_user, test_chat):
        """Test meeting flow with multiple votes."""
        
        # Create meeting
        meeting_data = {
            "title": "Voting Test Meeting",
            "description": "Meeting for testing voting",
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
        
        create_response = await test_client.post("/meetings", json=meeting_data)
        assert create_response.status_code == 201
        create_data = create_response.json()
        meeting_id = create_data["meeting_id"]
        
        # Resolve time slots
        with patch('src.services.scheduler.GoogleCalendarProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.get_free_busy_times.return_value = {
                "success": True,
                "free_busy_times": [
                    {
                        "start": (datetime.utcnow() + timedelta(days=1, hours=10)).isoformat(),
                        "end": (datetime.utcnow() + timedelta(days=1, hours=11)).isoformat(),
                        "available": True,
                    },
                    {
                        "start": (datetime.utcnow() + timedelta(days=1, hours=14)).isoformat(),
                        "end": (datetime.utcnow() + timedelta(days=1, hours=15)).isoformat(),
                        "available": True,
                    },
                ]
            }
            
            resolve_response = await test_client.post(f"/meetings/{meeting_id}/resolve")
            assert resolve_response.status_code == 200
            resolve_data = resolve_response.json()
            time_slots = resolve_data["time_slots"]
            
            # Get participant
            meeting_response = await test_client.get(f"/meetings/{meeting_id}")
            meeting_data = meeting_response.json()
            participant = meeting_data["meeting_data"]["participants"][0]
            
            # Vote on first time slot
            vote1_data = {
                "participant_id": participant["id"],
                "start_time": time_slots[0]["start"],
                "end_time": time_slots[0]["end"],
                "preference": "preferred",
            }
            
            vote1_response = await test_client.post(f"/meetings/{meeting_id}/vote", json=vote1_data)
            assert vote1_response.status_code == 200
            vote1_result = vote1_response.json()
            assert vote1_result["success"] is True
            
            # Vote on second time slot
            vote2_data = {
                "participant_id": participant["id"],
                "start_time": time_slots[1]["start"],
                "end_time": time_slots[1]["end"],
                "preference": "available",
            }
            
            vote2_response = await test_client.post(f"/meetings/{meeting_id}/vote", json=vote2_data)
            assert vote2_response.status_code == 200
            vote2_result = vote2_response.json()
            assert vote2_result["success"] is True
            
            # Get all votes
            votes_response = await test_client.get(f"/meetings/{meeting_id}/votes")
            assert votes_response.status_code == 200
            votes_data = votes_response.json()
            assert votes_data["success"] is True
            assert len(votes_data["votes"]) == 2
            
            # Verify vote preferences
            vote_preferences = [vote["preference"] for vote in votes_data["votes"]]
            assert "preferred" in vote_preferences
            assert "available" in vote_preferences
    
    @pytest.mark.asyncio
    async def test_meeting_flow_cancellation(self, test_client: AsyncClient, test_user, test_chat):
        """Test meeting flow with cancellation."""
        
        # Create meeting
        meeting_data = {
            "title": "Cancellation Test Meeting",
            "description": "Meeting for testing cancellation",
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
        
        create_response = await test_client.post("/meetings", json=meeting_data)
        assert create_response.status_code == 201
        create_data = create_response.json()
        meeting_id = create_data["meeting_id"]
        
        # Verify meeting is created
        get_response = await test_client.get(f"/meetings/{meeting_id}")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["meeting_data"]["status"] == "created"
        
        # Cancel meeting
        cancel_response = await test_client.delete(f"/meetings/{meeting_id}")
        assert cancel_response.status_code == 200
        cancel_data = cancel_response.json()
        assert cancel_data["success"] is True
        
        # Verify meeting is cancelled
        final_response = await test_client.get(f"/meetings/{meeting_id}")
        assert final_response.status_code == 200
        final_data = final_response.json()
        assert final_data["meeting_data"]["status"] == "cancelled"
