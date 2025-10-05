"""Unit tests for Notification service."""

import pytest
from unittest.mock import AsyncMock, patch

from src.services.notification import NotificationService


class TestNotificationService:
    """Test NotificationService."""
    
    @pytest.fixture
    def notification_service(self):
        """Create NotificationService instance."""
        return NotificationService()
    
    @pytest.mark.asyncio
    async def test_send_direct_message_success(self, notification_service):
        """Test sending direct message successfully."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.send_direct_message.return_value = True
            
            result = await notification_service.send_direct_message(
                chat_id=12345,
                message="Test message",
                parse_mode="Markdown"
            )
            
            assert result is True
            mock_provider.send_direct_message.assert_called_once_with(
                chat_id=12345,
                message="Test message",
                parse_mode="Markdown",
                reply_markup=None
            )
    
    @pytest.mark.asyncio
    async def test_send_direct_message_failure(self, notification_service):
        """Test sending direct message failure."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.send_direct_message.return_value = False
            
            result = await notification_service.send_direct_message(
                chat_id=12345,
                message="Test message"
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_direct_message_exception(self, notification_service):
        """Test sending direct message with exception."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.send_direct_message.side_effect = Exception("Network error")
            
            result = await notification_service.send_direct_message(
                chat_id=12345,
                message="Test message"
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_group_message_success(self, notification_service):
        """Test sending group message successfully."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.send_message.return_value = True
            
            result = await notification_service.send_group_message(
                chat_id=-1001234567890,
                message="Test group message",
                parse_mode="Markdown"
            )
            
            assert result is True
            mock_provider.send_message.assert_called_once_with(
                chat_id=-1001234567890,
                message="Test group message",
                parse_mode="Markdown",
                reply_markup=None
            )
    
    @pytest.mark.asyncio
    async def test_send_group_message_failure(self, notification_service):
        """Test sending group message failure."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.send_message.return_value = False
            
            result = await notification_service.send_group_message(
                chat_id=-1001234567890,
                message="Test group message"
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_edit_message_success(self, notification_service):
        """Test editing message successfully."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.edit_message_text.return_value = True
            
            result = await notification_service.edit_message(
                chat_id=12345,
                message_id=67890,
                text="Updated message",
                parse_mode="Markdown"
            )
            
            assert result is True
            mock_provider.edit_message_text.assert_called_once_with(
                chat_id=12345,
                message_id=67890,
                text="Updated message",
                parse_mode="Markdown",
                reply_markup=None
            )
    
    @pytest.mark.asyncio
    async def test_edit_message_failure(self, notification_service):
        """Test editing message failure."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.edit_message_text.return_value = False
            
            result = await notification_service.edit_message(
                chat_id=12345,
                message_id=67890,
                text="Updated message"
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_message_success(self, notification_service):
        """Test deleting message successfully."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.delete_message.return_value = True
            
            result = await notification_service.delete_message(
                chat_id=12345,
                message_id=67890
            )
            
            assert result is True
            mock_provider.delete_message.assert_called_once_with(
                chat_id=12345,
                message_id=67890
            )
    
    @pytest.mark.asyncio
    async def test_delete_message_failure(self, notification_service):
        """Test deleting message failure."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.delete_message.return_value = False
            
            result = await notification_service.delete_message(
                chat_id=12345,
                message_id=67890
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_meeting_created_notification(self, notification_service):
        """Test sending meeting created notification."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.send_message.return_value = True
            
            result = await notification_service.send_meeting_created_notification(
                chat_id=-1001234567890,
                meeting_title="Test Meeting",
                creator_username="testuser",
                participant_count=3
            )
            
            assert result is True
            mock_provider.send_message.assert_called_once()
            
            # Verify the message contains expected content
            call_args = mock_provider.send_message.call_args
            message = call_args[1]["message"]
            assert "Test Meeting" in message
            assert "testuser" in message
            assert "3" in message
    
    @pytest.mark.asyncio
    async def test_send_time_slots_ready_notification(self, notification_service):
        """Test sending time slots ready notification."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.send_direct_message.return_value = True
            
            time_slots = [
                {
                    "start": "2024-01-01T10:00:00Z",
                    "end": "2024-01-01T11:00:00Z",
                    "available_count": 3,
                },
                {
                    "start": "2024-01-01T14:00:00Z",
                    "end": "2024-01-01T15:00:00Z",
                    "available_count": 3,
                },
            ]
            
            result = await notification_service.send_time_slots_ready_notification(
                chat_id=12345,
                meeting_title="Test Meeting",
                time_slots=time_slots
            )
            
            assert result is True
            mock_provider.send_direct_message.assert_called_once()
            
            # Verify the message contains expected content
            call_args = mock_provider.send_direct_message.call_args
            message = call_args[1]["message"]
            assert "Test Meeting" in message
            assert "2" in message  # Number of time slots
    
    @pytest.mark.asyncio
    async def test_send_meeting_confirmed_notification(self, notification_service):
        """Test sending meeting confirmed notification."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.send_message.return_value = True
            
            result = await notification_service.send_meeting_confirmed_notification(
                chat_id=-1001234567890,
                meeting_title="Test Meeting",
                start_time="2024-01-01T10:00:00Z",
                end_time="2024-01-01T11:00:00Z"
            )
            
            assert result is True
            mock_provider.send_message.assert_called_once()
            
            # Verify the message contains expected content
            call_args = mock_provider.send_message.call_args
            message = call_args[1]["message"]
            assert "Test Meeting" in message
            assert "confirmed" in message.lower()
    
    @pytest.mark.asyncio
    async def test_send_oauth_reminder_notification(self, notification_service):
        """Test sending OAuth reminder notification."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.send_direct_message.return_value = True
            
            result = await notification_service.send_oauth_reminder_notification(
                chat_id=12345,
                reminder_type="consent"
            )
            
            assert result is True
            mock_provider.send_direct_message.assert_called_once()
            
            # Verify the message contains expected content
            call_args = mock_provider.send_direct_message.call_args
            message = call_args[1]["message"]
            assert "calendar" in message.lower()
            assert "link_calendar" in message
    
    @pytest.mark.asyncio
    async def test_send_error_notification(self, notification_service):
        """Test sending error notification."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.send_direct_message.return_value = True
            
            result = await notification_service.send_error_notification(
                chat_id=12345,
                error_message="Something went wrong",
                meeting_title="Test Meeting"
            )
            
            assert result is True
            mock_provider.send_direct_message.assert_called_once()
            
            # Verify the message contains expected content
            call_args = mock_provider.send_direct_message.call_args
            message = call_args[1]["message"]
            assert "error" in message.lower()
            assert "Something went wrong" in message
    
    @pytest.mark.asyncio
    async def test_notification_with_reply_markup(self, notification_service):
        """Test notification with reply markup."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.send_direct_message.return_value = True
            
            reply_markup = {"inline_keyboard": [["Test Button"]]}
            
            result = await notification_service.send_direct_message(
                chat_id=12345,
                message="Test message",
                reply_markup=reply_markup
            )
            
            assert result is True
            mock_provider.send_direct_message.assert_called_once_with(
                chat_id=12345,
                message="Test message",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
    
    @pytest.mark.asyncio
    async def test_batch_notification_sending(self, notification_service):
        """Test sending notifications to multiple users."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            mock_provider.send_direct_message.return_value = True
            
            chat_ids = [12345, 67890, 11111]
            
            results = await notification_service.send_batch_notifications(
                chat_ids=chat_ids,
                message="Batch notification message"
            )
            
            assert len(results) == 3
            assert all(result["success"] for result in results)
            assert mock_provider.send_direct_message.call_count == 3
    
    @pytest.mark.asyncio
    async def test_batch_notification_partial_failure(self, notification_service):
        """Test batch notification with partial failures."""
        # Mock the Telegram provider
        with patch('src.services.notification.TelegramProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider_class.return_value = mock_provider
            
            # Mock different responses for different chat IDs
            def mock_send_message(chat_id, **kwargs):
                return chat_id != 67890  # Fail for chat_id 67890
            
            mock_provider.send_direct_message.side_effect = mock_send_message
            
            chat_ids = [12345, 67890, 11111]
            
            results = await notification_service.send_batch_notifications(
                chat_ids=chat_ids,
                message="Batch notification message"
            )
            
            assert len(results) == 3
            assert results[0]["success"] is True
            assert results[1]["success"] is False
            assert results[2]["success"] is True
