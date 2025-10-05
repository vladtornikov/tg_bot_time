"""Unit tests for Meeting model."""

import pytest
from datetime import datetime, timedelta

from src.models.meeting import Meeting, MeetingParticipant


class TestMeeting:
    """Test Meeting model."""
    
    @pytest.mark.asyncio
    async def test_create_meeting(self, test_session, test_user, test_chat):
        """Test creating a meeting."""
        meeting = Meeting(
            title="Test Meeting",
            description="Test meeting description",
            creator_id=test_user.id,
            chat_id=test_chat.id,
            status="created",
            duration_minutes=60,
            earliest_start=datetime.utcnow() + timedelta(days=1),
            latest_end=datetime.utcnow() + timedelta(days=7),
            working_hours_start=9,
            working_hours_end=17,
            timezone="UTC",
        )
        
        test_session.add(meeting)
        await test_session.commit()
        await test_session.refresh(meeting)
        
        assert meeting.id is not None
        assert meeting.title == "Test Meeting"
        assert meeting.description == "Test meeting description"
        assert meeting.creator_id == test_user.id
        assert meeting.chat_id == test_chat.id
        assert meeting.status == "created"
        assert meeting.duration_minutes == 60
        assert meeting.working_hours_start == 9
        assert meeting.working_hours_end == 17
        assert meeting.timezone == "UTC"
        assert meeting.created_at is not None
        assert meeting.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_meeting_str_representation(self, test_meeting):
        """Test meeting string representation."""
        assert str(test_meeting) == "Test Meeting (created)"
    
    @pytest.mark.asyncio
    async def test_meeting_status_transitions(self, test_session, test_meeting):
        """Test meeting status transitions."""
        # Valid statuses
        valid_statuses = ["created", "time_slots_resolved", "voting", "confirmed", "completed", "cancelled"]
        
        for status in valid_statuses:
            test_meeting.status = status
            await test_session.commit()
            await test_session.refresh(test_meeting)
            assert test_meeting.status == status
    
    @pytest.mark.asyncio
    async def test_meeting_relationships(self, test_session, test_meeting, test_user, test_chat):
        """Test meeting relationships."""
        await test_session.refresh(test_meeting, ["creator", "chat"])
        
        assert test_meeting.creator is not None
        assert test_meeting.chat is not None
        assert test_meeting.creator.username == "testuser"
        assert test_meeting.chat.title == "Test Group"
    
    @pytest.mark.asyncio
    async def test_meeting_working_hours_validation(self, test_session, test_user, test_chat):
        """Test meeting working hours validation."""
        # Valid working hours
        meeting = Meeting(
            title="Test Meeting",
            creator_id=test_user.id,
            chat_id=test_chat.id,
            status="created",
            duration_minutes=60,
            earliest_start=datetime.utcnow() + timedelta(days=1),
            latest_end=datetime.utcnow() + timedelta(days=7),
            working_hours_start=9,
            working_hours_end=17,
            timezone="UTC",
        )
        
        test_session.add(meeting)
        await test_session.commit()
        await test_session.refresh(meeting)
        
        assert meeting.working_hours_start == 9
        assert meeting.working_hours_end == 17
    
    @pytest.mark.asyncio
    async def test_meeting_duration_validation(self, test_session, test_user, test_chat):
        """Test meeting duration validation."""
        # Valid durations
        valid_durations = [15, 30, 60, 90, 120, 240]
        
        for duration in valid_durations:
            meeting = Meeting(
                title=f"Test Meeting {duration}min",
                creator_id=test_user.id,
                chat_id=test_chat.id,
                status="created",
                duration_minutes=duration,
                earliest_start=datetime.utcnow() + timedelta(days=1),
                latest_end=datetime.utcnow() + timedelta(days=7),
                working_hours_start=9,
                working_hours_end=17,
                timezone="UTC",
            )
            
            test_session.add(meeting)
            await test_session.commit()
            await test_session.refresh(meeting)
            assert meeting.duration_minutes == duration
            await test_session.delete(meeting)
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_meeting_soft_delete(self, test_session, test_meeting):
        """Test meeting soft delete."""
        meeting_id = test_meeting.id
        
        # Soft delete the meeting
        test_meeting.deleted_at = datetime.utcnow()
        await test_session.commit()
        
        # Verify meeting is soft deleted
        assert test_meeting.deleted_at is not None
        assert test_meeting.is_deleted is True


class TestMeetingParticipant:
    """Test MeetingParticipant model."""
    
    @pytest.mark.asyncio
    async def test_create_meeting_participant(self, test_session, test_meeting, test_user):
        """Test creating a meeting participant."""
        participant = MeetingParticipant(
            meeting_id=test_meeting.id,
            user_id=test_user.id,
            telegram_chat_id=test_user.telegram_id,
            username=test_user.username,
            status="active",
        )
        
        test_session.add(participant)
        await test_session.commit()
        await test_session.refresh(participant)
        
        assert participant.id is not None
        assert participant.meeting_id == test_meeting.id
        assert participant.user_id == test_user.id
        assert participant.telegram_chat_id == test_user.telegram_id
        assert participant.username == test_user.username
        assert participant.status == "active"
        assert participant.created_at is not None
        assert participant.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_meeting_participant_str_representation(self, test_meeting_participant):
        """Test meeting participant string representation."""
        assert str(test_meeting_participant) == "Test User (@testuser)"
        
        # Test without username
        test_meeting_participant.username = None
        assert str(test_meeting_participant) == "Test User"
    
    @pytest.mark.asyncio
    async def test_meeting_participant_status_validation(self, test_session, test_meeting, test_user):
        """Test meeting participant status validation."""
        # Valid statuses
        valid_statuses = ["active", "inactive", "declined", "removed"]
        
        for status in valid_statuses:
            participant = MeetingParticipant(
                meeting_id=test_meeting.id,
                user_id=test_user.id,
                telegram_chat_id=test_user.telegram_id,
                username=test_user.username,
                status=status,
            )
            test_session.add(participant)
            await test_session.commit()
            await test_session.refresh(participant)
            assert participant.status == status
            await test_session.delete(participant)
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_meeting_participant_relationships(self, test_session, test_meeting_participant):
        """Test meeting participant relationships."""
        await test_session.refresh(test_meeting_participant, ["meeting", "user"])
        
        assert test_meeting_participant.meeting is not None
        assert test_meeting_participant.user is not None
        assert test_meeting_participant.meeting.title == "Test Meeting"
        assert test_meeting_participant.user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_meeting_participant_soft_delete(self, test_session, test_meeting_participant):
        """Test meeting participant soft delete."""
        participant_id = test_meeting_participant.id
        
        # Soft delete the participant
        test_meeting_participant.deleted_at = datetime.utcnow()
        await test_session.commit()
        
        # Verify participant is soft deleted
        assert test_meeting_participant.deleted_at is not None
        assert test_meeting_participant.is_deleted is True


class TestMeetingParticipantRelationships:
    """Test meeting participant relationships."""
    
    @pytest.mark.asyncio
    async def test_meeting_participants_relationship(self, test_session, test_meeting):
        """Test meeting-participants relationship."""
        # Create additional users and participants
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
        
        participant1 = MeetingParticipant(
            meeting_id=test_meeting.id,
            user_id=user1.id,
            telegram_chat_id=user1.telegram_id,
            username=user1.username,
            status="active",
        )
        participant2 = MeetingParticipant(
            meeting_id=test_meeting.id,
            user_id=user2.id,
            telegram_chat_id=user2.telegram_id,
            username=user2.username,
            status="active",
        )
        
        test_session.add_all([participant1, participant2])
        await test_session.commit()
        
        # Refresh meeting with participants
        await test_session.refresh(test_meeting, ["participants"])
        
        assert len(test_meeting.participants) == 3  # Including the one from fixture
        assert all(p.status == "active" for p in test_meeting.participants)
    
    @pytest.mark.asyncio
    async def test_user_meeting_participations_relationship(self, test_session, test_user):
        """Test user-meeting participations relationship."""
        # Create additional meetings and participants
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
        
        meeting1 = Meeting(
            title="Meeting 1",
            creator_id=test_user.id,
            chat_id=chat1.id,
            status="created",
            duration_minutes=60,
            earliest_start=datetime.utcnow() + timedelta(days=1),
            latest_end=datetime.utcnow() + timedelta(days=7),
            working_hours_start=9,
            working_hours_end=17,
            timezone="UTC",
        )
        meeting2 = Meeting(
            title="Meeting 2",
            creator_id=test_user.id,
            chat_id=chat2.id,
            status="created",
            duration_minutes=30,
            earliest_start=datetime.utcnow() + timedelta(days=1),
            latest_end=datetime.utcnow() + timedelta(days=7),
            working_hours_start=9,
            working_hours_end=17,
            timezone="UTC",
        )
        
        test_session.add_all([meeting1, meeting2])
        await test_session.commit()
        
        participant1 = MeetingParticipant(
            meeting_id=meeting1.id,
            user_id=test_user.id,
            telegram_chat_id=test_user.telegram_id,
            username=test_user.username,
            status="active",
        )
        participant2 = MeetingParticipant(
            meeting_id=meeting2.id,
            user_id=test_user.id,
            telegram_chat_id=test_user.telegram_id,
            username=test_user.username,
            status="active",
        )
        
        test_session.add_all([participant1, participant2])
        await test_session.commit()
        
        # Refresh user with participations
        await test_session.refresh(test_user, ["meeting_participations"])
        
        assert len(test_user.meeting_participations) == 3  # Including the one from fixture
        assert all(p.status == "active" for p in test_user.meeting_participations)
