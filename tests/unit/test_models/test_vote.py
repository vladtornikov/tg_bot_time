"""Unit tests for Vote model."""

import pytest
from datetime import datetime, timedelta

from src.models.vote import Vote


class TestVote:
    """Test Vote model."""
    
    @pytest.mark.asyncio
    async def test_create_vote(self, test_session, test_meeting_participant):
        """Test creating a vote."""
        vote = Vote(
            participant_id=test_meeting_participant.id,
            start_time=datetime.utcnow() + timedelta(days=1, hours=10),
            end_time=datetime.utcnow() + timedelta(days=1, hours=11),
            preference="available",
        )
        
        test_session.add(vote)
        await test_session.commit()
        await test_session.refresh(vote)
        
        assert vote.id is not None
        assert vote.participant_id == test_meeting_participant.id
        assert vote.start_time is not None
        assert vote.end_time is not None
        assert vote.preference == "available"
        assert vote.created_at is not None
        assert vote.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_vote_str_representation(self, test_vote):
        """Test vote string representation."""
        expected_str = f"Vote for {test_vote.start_time.strftime('%Y-%m-%d %H:%M')} - {test_vote.preference}"
        assert str(test_vote) == expected_str
    
    @pytest.mark.asyncio
    async def test_vote_preference_validation(self, test_session, test_meeting_participant):
        """Test vote preference validation."""
        # Valid preferences
        valid_preferences = ["available", "preferred", "unavailable", "maybe"]
        
        for preference in valid_preferences:
            vote = Vote(
                participant_id=test_meeting_participant.id,
                start_time=datetime.utcnow() + timedelta(days=1, hours=10),
                end_time=datetime.utcnow() + timedelta(days=1, hours=11),
                preference=preference,
            )
            
            test_session.add(vote)
            await test_session.commit()
            await test_session.refresh(vote)
            assert vote.preference == preference
            await test_session.delete(vote)
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_vote_time_validation(self, test_session, test_meeting_participant):
        """Test vote time validation."""
        # Valid time slot
        start_time = datetime.utcnow() + timedelta(days=1, hours=10)
        end_time = start_time + timedelta(hours=1)
        
        vote = Vote(
            participant_id=test_meeting_participant.id,
            start_time=start_time,
            end_time=end_time,
            preference="available",
        )
        
        test_session.add(vote)
        await test_session.commit()
        await test_session.refresh(vote)
        
        assert vote.start_time == start_time
        assert vote.end_time == end_time
        assert vote.end_time > vote.start_time
    
    @pytest.mark.asyncio
    async def test_vote_relationships(self, test_session, test_vote):
        """Test vote relationships."""
        await test_session.refresh(test_vote, ["participant"])
        
        assert test_vote.participant is not None
        assert test_vote.participant.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_vote_soft_delete(self, test_session, test_vote):
        """Test vote soft delete."""
        vote_id = test_vote.id
        
        # Soft delete the vote
        test_vote.deleted_at = datetime.utcnow()
        await test_session.commit()
        
        # Verify vote is soft deleted
        assert test_vote.deleted_at is not None
        assert test_vote.is_deleted is True
    
    @pytest.mark.asyncio
    async def test_vote_update(self, test_session, test_vote):
        """Test vote update."""
        original_preference = test_vote.preference
        new_preference = "preferred"
        
        # Update the vote
        test_vote.preference = new_preference
        
        await test_session.commit()
        await test_session.refresh(test_vote)
        
        assert test_vote.preference == new_preference
        assert test_vote.preference != original_preference
        assert test_vote.updated_at > test_vote.created_at
    
    @pytest.mark.asyncio
    async def test_vote_meeting_relationship(self, test_session, test_vote):
        """Test vote meeting relationship through participant."""
        await test_session.refresh(test_vote, ["participant", "participant.meeting"])
        
        assert test_vote.participant is not None
        assert test_vote.participant.meeting is not None
        assert test_vote.participant.meeting.title == "Test Meeting"
    
    @pytest.mark.asyncio
    async def test_vote_user_relationship(self, test_session, test_vote):
        """Test vote user relationship through participant."""
        await test_session.refresh(test_vote, ["participant", "participant.user"])
        
        assert test_vote.participant is not None
        assert test_vote.participant.user is not None
        assert test_vote.participant.user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_multiple_votes_per_participant(self, test_session, test_meeting_participant):
        """Test multiple votes per participant."""
        # Create multiple votes for the same participant
        vote1 = Vote(
            participant_id=test_meeting_participant.id,
            start_time=datetime.utcnow() + timedelta(days=1, hours=10),
            end_time=datetime.utcnow() + timedelta(days=1, hours=11),
            preference="available",
        )
        
        vote2 = Vote(
            participant_id=test_meeting_participant.id,
            start_time=datetime.utcnow() + timedelta(days=1, hours=14),
            end_time=datetime.utcnow() + timedelta(days=1, hours=15),
            preference="preferred",
        )
        
        vote3 = Vote(
            participant_id=test_meeting_participant.id,
            start_time=datetime.utcnow() + timedelta(days=2, hours=10),
            end_time=datetime.utcnow() + timedelta(days=2, hours=11),
            preference="unavailable",
        )
        
        test_session.add_all([vote1, vote2, vote3])
        await test_session.commit()
        
        # Refresh participant with votes
        await test_session.refresh(test_meeting_participant, ["votes"])
        
        assert len(test_meeting_participant.votes) == 4  # Including the one from fixture
        preferences = [vote.preference for vote in test_meeting_participant.votes]
        assert "available" in preferences
        assert "preferred" in preferences
        assert "unavailable" in preferences
    
    @pytest.mark.asyncio
    async def test_vote_time_slot_consistency(self, test_session, test_meeting_participant):
        """Test vote time slot consistency."""
        # Create votes with consistent time slots
        base_time = datetime.utcnow() + timedelta(days=1, hours=9)
        
        for hour in range(9, 17):  # 9 AM to 5 PM
            start_time = base_time + timedelta(hours=hour)
            end_time = start_time + timedelta(hours=1)
            
            vote = Vote(
                participant_id=test_meeting_participant.id,
                start_time=start_time,
                end_time=end_time,
                preference="available" if hour % 2 == 0 else "unavailable",
            )
            
            test_session.add(vote)
        
        await test_session.commit()
        
        # Refresh participant with votes
        await test_session.refresh(test_meeting_participant, ["votes"])
        
        assert len(test_meeting_participant.votes) == 9  # Including the one from fixture
        
        # Verify time slot consistency
        votes = sorted(test_meeting_participant.votes, key=lambda v: v.start_time)
        for i in range(1, len(votes)):
            assert votes[i].start_time >= votes[i-1].end_time or votes[i].start_time == votes[i-1].start_time
