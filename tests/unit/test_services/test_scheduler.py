"""Unit tests for Scheduler service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from src.services.scheduler import SchedulerService


class TestSchedulerService:
    """Test SchedulerService."""
    
    @pytest.fixture
    def scheduler_service(self):
        """Create SchedulerService instance."""
        return SchedulerService()
    
    @pytest.mark.asyncio
    async def test_resolve_meeting_time_slots(
        self, 
        scheduler_service, 
        test_session, 
        test_meeting, 
        test_meeting_participant
    ):
        """Test resolving meeting time slots."""
        # Mock the Google Calendar provider
        with patch('src.services.scheduler.GoogleCalendarProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            
            # Mock free busy times response
            mock_provider.get_free_busy_times.return_value = {
                "success": True,
                "free_busy_times": [
                    {
                        "start": "2024-01-01T10:00:00Z",
                        "end": "2024-01-01T11:00:00Z",
                        "available": True,
                    },
                    {
                        "start": "2024-01-01T14:00:00Z",
                        "end": "2024-01-01T15:00:00Z",
                        "available": True,
                    },
                    {
                        "start": "2024-01-01T16:00:00Z",
                        "end": "2024-01-01T17:00:00Z",
                        "available": False,
                    },
                ]
            }
            
            # Test resolving time slots
            result = await scheduler_service.resolve_meeting_time_slots(
                test_meeting.id, session=test_session
            )
            
            assert result["success"] is True
            assert "time_slots" in result
            assert len(result["time_slots"]) == 2  # Only available slots
    
    @pytest.mark.asyncio
    async def test_resolve_meeting_time_slots_no_participants(
        self, 
        scheduler_service, 
        test_session, 
        test_meeting
    ):
        """Test resolving time slots for meeting with no participants."""
        result = await scheduler_service.resolve_meeting_time_slots(
            test_meeting.id, session=test_session
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "No active participants" in result["error"]
    
    @pytest.mark.asyncio
    async def test_resolve_meeting_time_slots_invalid_meeting(
        self, 
        scheduler_service, 
        test_session
    ):
        """Test resolving time slots for invalid meeting."""
        result = await scheduler_service.resolve_meeting_time_slots(
            99999, session=test_session  # Non-existent meeting ID
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "Meeting not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_confirm_meeting_time(
        self, 
        scheduler_service, 
        test_session, 
        test_meeting,
        test_meeting_participant
    ):
        """Test confirming meeting time."""
        # Mock the Google Calendar provider
        with patch('src.services.scheduler.GoogleCalendarProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            
            # Mock calendar event creation
            mock_provider.create_calendar_event.return_value = {
                "success": True,
                "event_id": "test_event_id",
            }
            
            # Test confirming meeting time
            start_time = datetime.utcnow() + timedelta(days=1, hours=10)
            end_time = start_time + timedelta(hours=1)
            
            result = await scheduler_service.confirm_meeting_time(
                test_meeting.id,
                start_time,
                end_time,
                session=test_session
            )
            
            assert result["success"] is True
            assert "event_id" in result
            assert result["event_id"] == "test_event_id"
            
            # Verify meeting status was updated
            await test_session.refresh(test_meeting)
            assert test_meeting.status == "confirmed"
    
    @pytest.mark.asyncio
    async def test_confirm_meeting_time_invalid_meeting(
        self, 
        scheduler_service, 
        test_session
    ):
        """Test confirming time for invalid meeting."""
        start_time = datetime.utcnow() + timedelta(days=1, hours=10)
        end_time = start_time + timedelta(hours=1)
        
        result = await scheduler_service.confirm_meeting_time(
            99999,  # Non-existent meeting ID
            start_time,
            end_time,
            session=test_session
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "Meeting not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_cancel_meeting(
        self, 
        scheduler_service, 
        test_session, 
        test_meeting
    ):
        """Test cancelling a meeting."""
        result = await scheduler_service.cancel_meeting(
            test_meeting.id, session=test_session
        )
        
        assert result["success"] is True
        
        # Verify meeting status was updated
        await test_session.refresh(test_meeting)
        assert test_meeting.status == "cancelled"
    
    @pytest.mark.asyncio
    async def test_cancel_meeting_invalid(
        self, 
        scheduler_service, 
        test_session
    ):
        """Test cancelling invalid meeting."""
        result = await scheduler_service.cancel_meeting(
            99999, session=test_session  # Non-existent meeting ID
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "Meeting not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_meeting_status(
        self, 
        scheduler_service, 
        test_session, 
        test_meeting
    ):
        """Test getting meeting status."""
        result = await scheduler_service.get_meeting_status(
            test_meeting.id, session=test_session
        )
        
        assert result["success"] is True
        assert result["meeting_id"] == test_meeting.id
        assert result["status"] == "created"
        assert result["title"] == "Test Meeting"
    
    @pytest.mark.asyncio
    async def test_get_meeting_status_invalid(
        self, 
        scheduler_service, 
        test_session
    ):
        """Test getting status for invalid meeting."""
        result = await scheduler_service.get_meeting_status(
            99999, session=test_session  # Non-existent meeting ID
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "Meeting not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_compute_working_hours_intersection(self, scheduler_service):
        """Test computing working hours intersection."""
        # Test case 1: Same working hours
        working_hours1 = {"start": 9, "end": 17}
        working_hours2 = {"start": 9, "end": 17}
        
        result = scheduler_service.compute_working_hours_intersection(
            working_hours1, working_hours2
        )
        
        assert result == {"start": 9, "end": 17}
        
        # Test case 2: Partial overlap
        working_hours1 = {"start": 9, "end": 17}
        working_hours2 = {"start": 13, "end": 21}
        
        result = scheduler_service.compute_working_hours_intersection(
            working_hours1, working_hours2
        )
        
        assert result == {"start": 13, "end": 17}
        
        # Test case 3: No overlap
        working_hours1 = {"start": 9, "end": 17}
        working_hours2 = {"start": 18, "end": 22}
        
        result = scheduler_service.compute_working_hours_intersection(
            working_hours1, working_hours2
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_time_slot_candidates(self, scheduler_service):
        """Test generating time slot candidates."""
        # Test parameters
        start_date = datetime(2024, 1, 1, 9, 0, 0)  # 9 AM
        end_date = datetime(2024, 1, 1, 17, 0, 0)   # 5 PM
        duration_minutes = 60
        working_hours = {"start": 9, "end": 17}
        
        candidates = scheduler_service.generate_time_slot_candidates(
            start_date, end_date, duration_minutes, working_hours
        )
        
        assert len(candidates) == 8  # 8 hours of working time
        assert all(candidate["duration_minutes"] == 60 for candidate in candidates)
        assert all(
            candidate["start"].hour >= 9 and candidate["end"].hour <= 17
            for candidate in candidates
        )
    
    @pytest.mark.asyncio
    async def test_filter_available_time_slots(self, scheduler_service):
        """Test filtering available time slots."""
        # Test data
        candidates = [
            {
                "start": datetime(2024, 1, 1, 10, 0, 0),
                "end": datetime(2024, 1, 1, 11, 0, 0),
                "duration_minutes": 60,
            },
            {
                "start": datetime(2024, 1, 1, 11, 0, 0),
                "end": datetime(2024, 1, 1, 12, 0, 0),
                "duration_minutes": 60,
            },
            {
                "start": datetime(2024, 1, 1, 14, 0, 0),
                "end": datetime(2024, 1, 1, 15, 0, 0),
                "duration_minutes": 60,
            },
        ]
        
        free_busy_times = [
            {
                "start": datetime(2024, 1, 1, 10, 0, 0),
                "end": datetime(2024, 1, 1, 11, 0, 0),
                "available": True,
            },
            {
                "start": datetime(2024, 1, 1, 11, 0, 0),
                "end": datetime(2024, 1, 1, 12, 0, 0),
                "available": False,
            },
            {
                "start": datetime(2024, 1, 1, 14, 0, 0),
                "end": datetime(2024, 1, 1, 15, 0, 0),
                "available": True,
            },
        ]
        
        available_slots = scheduler_service.filter_available_time_slots(
            candidates, free_busy_times
        )
        
        assert len(available_slots) == 2  # Only available slots
        assert available_slots[0]["start"] == datetime(2024, 1, 1, 10, 0, 0)
        assert available_slots[1]["start"] == datetime(2024, 1, 1, 14, 0, 0)
    
    @pytest.mark.asyncio
    async def test_paginate_time_slots(self, scheduler_service):
        """Test paginating time slots."""
        # Create test time slots
        time_slots = []
        for i in range(20):
            time_slots.append({
                "start": datetime(2024, 1, 1, 9 + i, 0, 0),
                "end": datetime(2024, 1, 1, 10 + i, 0, 0),
                "duration_minutes": 60,
                "available_count": 5 - (i % 3),
            })
        
        # Test pagination
        page1 = scheduler_service.paginate_time_slots(time_slots, page=1, per_page=5)
        assert len(page1["time_slots"]) == 5
        assert page1["page"] == 1
        assert page1["per_page"] == 5
        assert page1["total"] == 20
        assert page1["total_pages"] == 4
        
        # Test last page
        page4 = scheduler_service.paginate_time_slots(time_slots, page=4, per_page=5)
        assert len(page4["time_slots"]) == 5
        assert page4["page"] == 4
        
        # Test empty page
        page5 = scheduler_service.paginate_time_slots(time_slots, page=5, per_page=5)
        assert len(page5["time_slots"]) == 0
