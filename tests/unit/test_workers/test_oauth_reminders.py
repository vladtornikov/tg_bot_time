"""Unit tests for OAuth reminder worker tasks."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from src.workers.oauth_reminders import (
    send_oauth_reminder,
    schedule_oauth_reminders,
    cancel_oauth_reminders,
)


class TestOAuthReminderTasks:
    """Test OAuth reminder worker tasks."""
    
    @pytest.mark.asyncio
    async def test_send_oauth_reminder_success(self, test_user, test_oauth_token):
        """Test sending OAuth reminder successfully."""
        # Mock the notification service
        with patch('src.workers.oauth_reminders.NotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.send_direct_message.return_value = True
            
            # Mock the database session
            with patch('src.workers.oauth_reminders.get_db_session') as mock_get_session:
                mock_session = AsyncMock()
                mock_get_session.return_value.__aenter__.return_value = mock_session
                
                # Mock user query
                mock_session.execute.return_value.scalar_one_or_none.return_value = test_user
                mock_session.refresh.return_value = None
                mock_session.commit.return_value = None
                
                # Execute the task
                result = send_oauth_reminder.apply(
                    args=[test_user.id, test_user.telegram_id, "consent"]
                )
                
                assert result.successful()
                task_result = result.result
                assert task_result["success"] is True
                assert task_result["user_id"] == test_user.id
                assert task_result["reminder_type"] == "consent"
    
    @pytest.mark.asyncio
    async def test_send_oauth_reminder_user_not_found(self):
        """Test sending OAuth reminder when user not found."""
        # Mock the database session
        with patch('src.workers.oauth_reminders.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock user query returning None
            mock_session.execute.return_value.scalar_one_or_none.return_value = None
            
            # Execute the task
            result = send_oauth_reminder.apply(
                args=[99999, 12345, "consent"]
            )
            
            assert result.successful()
            task_result = result.result
            assert task_result["success"] is False
            assert "User not found" in task_result["error"]
    
    @pytest.mark.asyncio
    async def test_send_oauth_reminder_user_has_valid_token(self, test_user, test_oauth_token):
        """Test sending OAuth reminder when user has valid token."""
        # Mock the database session
        with patch('src.workers.oauth_reminders.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock user with valid OAuth token
            test_user.oauth_token = test_oauth_token
            mock_session.execute.return_value.scalar_one_or_none.return_value = test_user
            mock_session.refresh.return_value = None
            
            # Execute the task
            result = send_oauth_reminder.apply(
                args=[test_user.id, test_user.telegram_id, "consent"]
            )
            
            assert result.successful()
            task_result = result.result
            assert task_result["success"] is False
            assert "already has valid OAuth token" in task_result["error"]
    
    @pytest.mark.asyncio
    async def test_send_oauth_reminder_message_failure(self, test_user):
        """Test sending OAuth reminder when message sending fails."""
        # Mock the notification service
        with patch('src.workers.oauth_reminders.NotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.send_direct_message.return_value = False
            
            # Mock the database session
            with patch('src.workers.oauth_reminders.get_db_session') as mock_get_session:
                mock_session = AsyncMock()
                mock_get_session.return_value.__aenter__.return_value = mock_session
                
                # Mock user query
                mock_session.execute.return_value.scalar_one_or_none.return_value = test_user
                mock_session.refresh.return_value = None
                
                # Execute the task
                result = send_oauth_reminder.apply(
                    args=[test_user.id, test_user.telegram_id, "consent"]
                )
                
                assert result.successful()
                task_result = result.result
                assert task_result["success"] is False
                assert "Failed to send message" in task_result["error"]
    
    @pytest.mark.asyncio
    async def test_send_oauth_reminder_database_error(self, test_user):
        """Test sending OAuth reminder with database error."""
        # Mock the database session
        with patch('src.workers.oauth_reminders.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock database error
            mock_session.execute.side_effect = Exception("Database error")
            
            # Execute the task
            result = send_oauth_reminder.apply(
                args=[test_user.id, test_user.telegram_id, "consent"]
            )
            
            # Should retry and eventually fail
            assert not result.successful()
    
    @pytest.mark.asyncio
    async def test_schedule_oauth_reminders_success(self, test_meeting, test_user):
        """Test scheduling OAuth reminders successfully."""
        # Mock the database session
        with patch('src.workers.oauth_reminders.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock participants needing consent
            mock_participants = [
                {
                    "user_id": test_user.id,
                    "telegram_chat_id": test_user.telegram_id,
                    "username": test_user.username,
                }
            ]
            
            # Mock the async function
            with patch('src.workers.oauth_reminders._get_participants_needing_consent') as mock_get_participants:
                mock_get_participants.return_value = mock_participants
                
                # Mock task scheduling
                with patch('src.workers.oauth_reminders.send_oauth_reminder.apply_async') as mock_apply_async:
                    mock_task = MagicMock()
                    mock_task.id = "test_task_id"
                    mock_apply_async.return_value = mock_task
                    
                    # Execute the task
                    result = schedule_oauth_reminders.apply(
                        args=[test_meeting.id]
                    )
                    
                    assert result.successful()
                    task_result = result.result
                    assert task_result["success"] is True
                    assert task_result["meeting_id"] == test_meeting.id
                    assert task_result["scheduled_count"] == 1
                    assert len(task_result["reminders"]) == 1
                    
                    # Verify tasks were scheduled
                    assert mock_apply_async.call_count == 2  # Immediate + follow-up
    
    @pytest.mark.asyncio
    async def test_schedule_oauth_reminders_no_participants(self, test_meeting):
        """Test scheduling OAuth reminders when no participants need consent."""
        # Mock the database session
        with patch('src.workers.oauth_reminders.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock no participants needing consent
            with patch('src.workers.oauth_reminders._get_participants_needing_consent') as mock_get_participants:
                mock_get_participants.return_value = []
                
                # Execute the task
                result = schedule_oauth_reminders.apply(
                    args=[test_meeting.id]
                )
                
                assert result.successful()
                task_result = result.result
                assert task_result["success"] is True
                assert task_result["scheduled_count"] == 0
                assert len(task_result["reminders"]) == 0
    
    @pytest.mark.asyncio
    async def test_cancel_oauth_reminders_success(self, test_user):
        """Test cancelling OAuth reminders successfully."""
        # Mock Celery app control
        with patch('src.workers.oauth_reminders.celery_app.control.inspect') as mock_inspect:
            mock_inspector = MagicMock()
            mock_inspect.return_value = mock_inspector
            
            # Mock active tasks
            mock_inspector.active.return_value = {
                "worker1": [
                    {
                        "name": "src.workers.oauth_reminders.send_oauth_reminder",
                        "args": [test_user.id, test_user.telegram_id, "consent"],
                        "id": "task_123"
                    }
                ]
            }
            
            # Mock task revocation
            with patch('src.workers.oauth_reminders.celery_app.control.revoke') as mock_revoke:
                # Execute the task
                result = cancel_oauth_reminders.apply(
                    args=[test_user.id, None]
                )
                
                assert result.successful()
                task_result = result.result
                assert task_result["success"] is True
                assert task_result["user_id"] == test_user.id
                assert len(task_result["cancelled_tasks"]) == 1
                assert task_result["cancelled_tasks"][0] == "task_123"
                
                # Verify revoke was called
                mock_revoke.assert_called_once_with("task_123", terminate=True)
    
    @pytest.mark.asyncio
    async def test_cancel_oauth_reminders_no_active_tasks(self, test_user):
        """Test cancelling OAuth reminders when no active tasks."""
        # Mock Celery app control
        with patch('src.workers.oauth_reminders.celery_app.control.inspect') as mock_inspect:
            mock_inspector = MagicMock()
            mock_inspect.return_value = mock_inspector
            
            # Mock no active tasks
            mock_inspector.active.return_value = {}
            
            # Execute the task
            result = cancel_oauth_reminders.apply(
                args=[test_user.id, None]
            )
            
            assert result.successful()
            task_result = result.result
            assert task_result["success"] is True
            assert task_result["user_id"] == test_user.id
            assert len(task_result["cancelled_tasks"]) == 0
    
    @pytest.mark.asyncio
    async def test_cancel_oauth_reminders_control_error(self, test_user):
        """Test cancelling OAuth reminders with control error."""
        # Mock Celery app control
        with patch('src.workers.oauth_reminders.celery_app.control.inspect') as mock_inspect:
            mock_inspector = MagicMock()
            mock_inspect.return_value = mock_inspector
            
            # Mock control error
            mock_inspector.active.side_effect = Exception("Control error")
            
            # Execute the task
            result = cancel_oauth_reminders.apply(
                args=[test_user.id, None]
            )
            
            # Should retry and eventually fail
            assert not result.successful()
    
    @pytest.mark.asyncio
    async def test_send_oauth_reminder_retry_logic(self, test_user):
        """Test OAuth reminder retry logic."""
        # Mock the database session to fail initially
        with patch('src.workers.oauth_reminders.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock database error
            mock_session.execute.side_effect = Exception("Database error")
            
            # Execute the task with retry
            result = send_oauth_reminder.apply(
                args=[test_user.id, test_user.telegram_id, "consent"]
            )
            
            # Should retry and eventually fail
            assert not result.successful()
            assert result.traceback is not None
    
    @pytest.mark.asyncio
    async def test_reminder_message_content(self):
        """Test reminder message content generation."""
        from src.workers.oauth_reminders import (
            _get_consent_reminder_message,
            _get_refresh_reminder_message,
            _get_general_reminder_message,
        )
        
        # Test consent reminder message
        consent_msg = _get_consent_reminder_message()
        assert "Calendar Access Required" in consent_msg
        assert "link_calendar" in consent_msg
        
        # Test refresh reminder message
        refresh_msg = _get_refresh_reminder_message()
        assert "Calendar Access Expired" in refresh_msg
        assert "link_calendar" in refresh_msg
        
        # Test general reminder message
        general_msg = _get_general_reminder_message()
        assert "Calendar Integration Needed" in general_msg
        assert "link_calendar" in general_msg
    
    @pytest.mark.asyncio
    async def test_reminder_types(self, test_user):
        """Test different reminder types."""
        reminder_types = ["consent", "refresh", "general"]
        
        for reminder_type in reminder_types:
            # Mock the notification service
            with patch('src.workers.oauth_reminders.NotificationService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                mock_service.send_direct_message.return_value = True
                
                # Mock the database session
                with patch('src.workers.oauth_reminders.get_db_session') as mock_get_session:
                    mock_session = AsyncMock()
                    mock_get_session.return_value.__aenter__.return_value = mock_session
                    
                    # Mock user query
                    mock_session.execute.return_value.scalar_one_or_none.return_value = test_user
                    mock_session.refresh.return_value = None
                    mock_session.commit.return_value = None
                    
                    # Execute the task
                    result = send_oauth_reminder.apply(
                        args=[test_user.id, test_user.telegram_id, reminder_type]
                    )
                    
                    assert result.successful()
                    task_result = result.result
                    assert task_result["success"] is True
                    assert task_result["reminder_type"] == reminder_type
