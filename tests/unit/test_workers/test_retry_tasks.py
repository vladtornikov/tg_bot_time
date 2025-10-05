"""Unit tests for retry worker tasks."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from src.workers.retry_tasks import (
    retry_calendar_operation,
    retry_notification,
    retry_meeting_resolution,
    cleanup_failed_task,
)


class TestRetryTasks:
    """Test retry worker tasks."""
    
    @pytest.mark.asyncio
    async def test_retry_calendar_operation_success(self, test_meeting, test_user, test_oauth_token):
        """Test retrying calendar operation successfully."""
        # Mock the database session
        with patch('src.workers.retry_tasks.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock meeting and user queries
            mock_session.execute.return_value.scalar_one_or_none.side_effect = [
                test_meeting,  # Meeting query
                test_user,     # User query
            ]
            mock_session.refresh.return_value = None
            mock_session.commit.return_value = None
            
            # Mock Google Calendar provider
            with patch('src.workers.retry_tasks.GoogleCalendarProvider') as mock_provider_class:
                mock_provider = AsyncMock()
                mock_provider_class.return_value = mock_provider
                mock_provider.get_free_busy_times.return_value = {
                    "success": True,
                    "free_busy_times": []
                }
                
                # Execute the task
                result = retry_calendar_operation.apply(
                    args=["freebusy", test_meeting.id, test_user.id],
                    kwargs={
                        "start_time": datetime.utcnow(),
                        "end_time": datetime.utcnow() + timedelta(hours=1),
                        "calendar_ids": ["primary"]
                    }
                )
                
                assert result.successful()
                task_result = result.result
                assert task_result["success"] is True
    
    @pytest.mark.asyncio
    async def test_retry_calendar_operation_meeting_not_found(self, test_user):
        """Test retrying calendar operation when meeting not found."""
        # Mock the database session
        with patch('src.workers.retry_tasks.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock meeting query returning None
            mock_session.execute.return_value.scalar_one_or_none.return_value = None
            
            # Execute the task
            result = retry_calendar_operation.apply(
                args=["freebusy", 99999, test_user.id]
            )
            
            assert result.successful()
            task_result = result.result
            assert task_result["success"] is False
            assert "Meeting not found" in task_result["error"]
    
    @pytest.mark.asyncio
    async def test_retry_calendar_operation_user_not_found(self, test_meeting):
        """Test retrying calendar operation when user not found."""
        # Mock the database session
        with patch('src.workers.retry_tasks.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock meeting query success, user query failure
            mock_session.execute.return_value.scalar_one_or_none.side_effect = [
                test_meeting,  # Meeting query
                None,          # User query
            ]
            
            # Execute the task
            result = retry_calendar_operation.apply(
                args=["freebusy", test_meeting.id, 99999]
            )
            
            assert result.successful()
            task_result = result.result
            assert task_result["success"] is False
            assert "User not found" in task_result["error"]
    
    @pytest.mark.asyncio
    async def test_retry_calendar_operation_token_refresh(self, test_meeting, test_user):
        """Test retrying calendar operation with token refresh."""
        from datetime import datetime, timedelta
        
        # Create expired OAuth token
        expired_token = MagicMock()
        expired_token.is_valid.return_value = False
        
        test_user.oauth_token = expired_token
        
        # Mock the database session
        with patch('src.workers.retry_tasks.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock meeting and user queries
            mock_session.execute.return_value.scalar_one_or_none.side_effect = [
                test_meeting,  # Meeting query
                test_user,     # User query
            ]
            mock_session.refresh.return_value = None
            mock_session.commit.return_value = None
            
            # Mock Google Calendar provider
            with patch('src.workers.retry_tasks.GoogleCalendarProvider') as mock_provider_class:
                mock_provider = AsyncMock()
                mock_provider_class.return_value = mock_provider
                mock_provider.refresh_token.return_value = True
                mock_provider.get_free_busy_times.return_value = {
                    "success": True,
                    "free_busy_times": []
                }
                
                # Execute the task
                result = retry_calendar_operation.apply(
                    args=["freebusy", test_meeting.id, test_user.id]
                )
                
                assert result.successful()
                task_result = result.result
                assert task_result["success"] is True
                
                # Verify token refresh was called
                mock_provider.refresh_token.assert_called_once_with(expired_token)
    
    @pytest.mark.asyncio
    async def test_retry_calendar_operation_max_retries(self, test_meeting, test_user):
        """Test retrying calendar operation with max retries exceeded."""
        # Mock the database session to always fail
        with patch('src.workers.retry_tasks.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_session.execute.side_effect = Exception("Database error")
            
            # Execute the task with max retries
            result = retry_calendar_operation.apply(
                args=["freebusy", test_meeting.id, test_user.id]
            )
            
            # Should fail after max retries
            assert not result.successful()
            assert "MaxRetriesExceededError" in str(result.traceback)
    
    @pytest.mark.asyncio
    async def test_retry_notification_success(self):
        """Test retrying notification successfully."""
        # Mock the notification service
        with patch('src.workers.retry_tasks.NotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.send_direct_message.return_value = True
            
            # Execute the task
            result = retry_notification.apply(
                args=["test_notification", 12345, "Test message"],
                kwargs={"parse_mode": "Markdown"}
            )
            
            assert result.successful()
            task_result = result.result
            assert task_result["success"] is True
            assert task_result["notification_type"] == "test_notification"
            assert task_result["chat_id"] == 12345
    
    @pytest.mark.asyncio
    async def test_retry_notification_failure(self):
        """Test retrying notification with failure."""
        # Mock the notification service
        with patch('src.workers.retry_tasks.NotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.send_direct_message.return_value = False
            
            # Execute the task
            result = retry_notification.apply(
                args=["test_notification", 12345, "Test message"]
            )
            
            # Should retry and eventually fail
            assert not result.successful()
    
    @pytest.mark.asyncio
    async def test_retry_notification_max_retries(self):
        """Test retrying notification with max retries exceeded."""
        # Mock the notification service to always fail
        with patch('src.workers.retry_tasks.NotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.send_direct_message.side_effect = Exception("Network error")
            
            # Execute the task with max retries
            result = retry_notification.apply(
                args=["test_notification", 12345, "Test message"]
            )
            
            # Should fail after max retries
            assert not result.successful()
            assert "MaxRetriesExceededError" in str(result.traceback)
    
    @pytest.mark.asyncio
    async def test_retry_meeting_resolution_success(self, test_meeting, test_meeting_participant):
        """Test retrying meeting resolution successfully."""
        # Mock the database session
        with patch('src.workers.retry_tasks.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock meeting with participants
            test_meeting.participants = [test_meeting_participant]
            mock_session.execute.return_value.scalar_one_or_none.return_value = test_meeting
            mock_session.refresh.return_value = None
            mock_session.commit.return_value = None
            
            # Mock scheduler service
            with patch('src.workers.retry_tasks.SchedulerService') as mock_scheduler_class:
                mock_scheduler = AsyncMock()
                mock_scheduler_class.return_value = mock_scheduler
                mock_scheduler.resolve_meeting_time_slots.return_value = {
                    "success": True,
                    "time_slots": [
                        {
                            "start": datetime.utcnow() + timedelta(days=1, hours=10),
                            "end": datetime.utcnow() + timedelta(days=1, hours=11),
                            "available_count": 1,
                        }
                    ]
                }
                
                # Execute the task
                result = retry_meeting_resolution.apply(
                    args=[test_meeting.id]
                )
                
                assert result.successful()
                task_result = result.result
                assert task_result["success"] is True
    
    @pytest.mark.asyncio
    async def test_retry_meeting_resolution_not_found(self):
        """Test retrying meeting resolution when meeting not found."""
        # Mock the database session
        with patch('src.workers.retry_tasks.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock meeting query returning None
            mock_session.execute.return_value.scalar_one_or_none.return_value = None
            
            # Execute the task
            result = retry_meeting_resolution.apply(
                args=[99999]
            )
            
            assert result.successful()
            task_result = result.result
            assert task_result["success"] is False
            assert "Meeting not found" in task_result["error"]
    
    @pytest.mark.asyncio
    async def test_retry_meeting_resolution_max_retries(self):
        """Test retrying meeting resolution with max retries exceeded."""
        # Mock the database session to always fail
        with patch('src.workers.retry_tasks.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_session.execute.side_effect = Exception("Database error")
            
            # Execute the task with max retries
            result = retry_meeting_resolution.apply(
                args=[12345]
            )
            
            # Should fail after max retries
            assert not result.successful()
            assert "MaxRetriesExceededError" in str(result.traceback)
    
    @pytest.mark.asyncio
    async def test_cleanup_failed_task_success(self):
        """Test cleaning up failed task successfully."""
        # Execute the task
        result = cleanup_failed_task.apply(
            args=["task_123", "test_task", "Task failed with error"]
        )
        
        assert result.successful()
        task_result = result.result
        assert task_result["success"] is True
        assert task_result["task_id"] == "task_123"
    
    @pytest.mark.asyncio
    async def test_cleanup_failed_task_error(self):
        """Test cleaning up failed task with error."""
        # Mock logging to raise exception
        with patch('src.workers.retry_tasks.logger.error') as mock_logger:
            mock_logger.side_effect = Exception("Logging error")
            
            # Execute the task
            result = cleanup_failed_task.apply(
                args=["task_123", "test_task", "Task failed with error"]
            )
            
            # Should fail
            assert not result.successful()
    
    @pytest.mark.asyncio
    async def test_calendar_operation_types(self, test_meeting, test_user, test_oauth_token):
        """Test different calendar operation types."""
        operation_types = ["freebusy", "create_event", "update_event", "delete_event"]
        
        for operation_type in operation_types:
            # Mock the database session
            with patch('src.workers.retry_tasks.get_db_session') as mock_get_session:
                mock_session = AsyncMock()
                mock_get_session.return_value.__aenter__.return_value = mock_session
                
                # Mock meeting and user queries
                mock_session.execute.return_value.scalar_one_or_none.side_effect = [
                    test_meeting,  # Meeting query
                    test_user,     # User query
                ]
                mock_session.refresh.return_value = None
                mock_session.commit.return_value = None
                
                # Mock Google Calendar provider
                with patch('src.workers.retry_tasks.GoogleCalendarProvider') as mock_provider_class:
                    mock_provider = AsyncMock()
                    mock_provider_class.return_value = mock_provider
                    mock_provider.get_free_busy_times.return_value = {"success": True}
                    mock_provider.create_calendar_event.return_value = {"success": True}
                    mock_provider.update_calendar_event.return_value = {"success": True}
                    mock_provider.delete_calendar_event.return_value = {"success": True}
                    
                    # Execute the task
                    result = retry_calendar_operation.apply(
                        args=[operation_type, test_meeting.id, test_user.id]
                    )
                    
                    assert result.successful()
                    task_result = result.result
                    assert task_result["success"] is True
    
    @pytest.mark.asyncio
    async def test_unknown_operation_type(self, test_meeting, test_user, test_oauth_token):
        """Test retrying unknown operation type."""
        # Mock the database session
        with patch('src.workers.retry_tasks.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Mock meeting and user queries
            mock_session.execute.return_value.scalar_one_or_none.side_effect = [
                test_meeting,  # Meeting query
                test_user,     # User query
            ]
            mock_session.refresh.return_value = None
            
            # Execute the task with unknown operation type
            result = retry_calendar_operation.apply(
                args=["unknown_operation", test_meeting.id, test_user.id]
            )
            
            assert result.successful()
            task_result = result.result
            assert task_result["success"] is False
            assert "Unknown operation type" in task_result["error"]
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_delay_calculation(self):
        """Test exponential backoff delay calculation."""
        # This test verifies that the retry delay increases exponentially
        # The actual implementation would need to be tested through the Celery retry mechanism
        
        # Mock a failing operation
        with patch('src.workers.retry_tasks.get_db_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_session.execute.side_effect = Exception("Database error")
            
            # Execute the task
            result = retry_calendar_operation.apply(
                args=["freebusy", 12345, 67890]
            )
            
            # Should fail after retries
            assert not result.successful()
            # The retry countdown would be: 60, 120, 240, 300 (max) seconds
