"""Retry tasks for failed operations."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from celery.exceptions import Retry, MaxRetriesExceededError
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db_session
from src.models.meeting import Meeting, MeetingParticipant
from src.models.oauth import OAuthToken
from src.models.user import User
from src.providers.google import GoogleCalendarProvider
from src.services.notification import NotificationService
from src.services.scheduler import SchedulerService
from src.workers.celery_app import retry_task, celery_app

logger = logging.getLogger(__name__)


@retry_task(bind=True, max_retries=5, default_retry_delay=60)
def retry_calendar_operation(self, operation_type: str, meeting_id: int, user_id: int, **kwargs):
    """
    Retry failed calendar operations with exponential backoff.
    
    Args:
        operation_type: Type of operation (freebusy, create_event, etc.)
        meeting_id: Meeting ID
        user_id: User ID
        **kwargs: Additional operation-specific parameters
    """
    try:
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _retry_calendar_operation_async(operation_type, meeting_id, user_id, **kwargs)
            )
            return result
        finally:
            loop.close()
    except Exception as exc:
        # Calculate exponential backoff delay
        delay = min(300, 60 * (2 ** self.request.retries))  # Max 5 minutes
        
        if self.request.retries >= self.max_retries:
            # Log permanent failure
            logger.error(
                f"Calendar operation {operation_type} permanently failed for meeting {meeting_id}",
                extra={
                    "operation_type": operation_type,
                    "meeting_id": meeting_id,
                    "user_id": user_id,
                    "retries": self.request.retries,
                    "error": str(exc),
                }
            )
            raise MaxRetriesExceededError(f"Max retries exceeded for {operation_type}")
        
        # Retry with exponential backoff
        raise self.retry(countdown=delay, exc=exc)


async def _retry_calendar_operation_async(
    operation_type: str, 
    meeting_id: int, 
    user_id: int, 
    **kwargs
) -> Dict[str, Any]:
    """Async implementation of calendar operation retry."""
    async with get_db_session() as session:
        try:
            # Get meeting and user info
            meeting = await _get_meeting(session, meeting_id)
            user = await _get_user_with_oauth(session, user_id)
            
            if not meeting or not user or not user.oauth_token:
                return {"success": False, "error": "Meeting or user not found"}
            
            # Check if OAuth token is still valid
            if not user.oauth_token.is_valid():
                # Try to refresh the token
                provider = GoogleCalendarProvider()
                refreshed = await provider.refresh_token(user.oauth_token)
                
                if not refreshed:
                    return {"success": False, "error": "OAuth token refresh failed"}
            
            # Perform the specific operation
            result = await _perform_calendar_operation(
                operation_type, meeting, user, **kwargs
            )
            
            if result["success"]:
                # Update meeting status if needed
                await _update_meeting_status(session, meeting_id, operation_type)
                await session.commit()
            
            return result
            
        except Exception as e:
            await session.rollback()
            raise e


@retry_task(bind=True, max_retries=3, default_retry_delay=30)
def retry_notification(self, notification_type: str, chat_id: int, message: str, **kwargs):
    """
    Retry failed notification operations.
    
    Args:
        notification_type: Type of notification (meeting_created, vote_cast, etc.)
        chat_id: Telegram chat ID
        message: Message to send
        **kwargs: Additional notification parameters
    """
    try:
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _retry_notification_async(notification_type, chat_id, message, **kwargs)
            )
            return result
        finally:
            loop.close()
    except Exception as exc:
        delay = min(120, 30 * (2 ** self.request.retries))  # Max 2 minutes
        
        if self.request.retries >= self.max_retries:
            logger.error(
                f"Notification {notification_type} permanently failed for chat {chat_id}",
                extra={
                    "notification_type": notification_type,
                    "chat_id": chat_id,
                    "retries": self.request.retries,
                    "error": str(exc),
                }
            )
            raise MaxRetriesExceededError(f"Max retries exceeded for notification")
        
        raise self.retry(countdown=delay, exc=exc)


async def _retry_notification_async(
    notification_type: str, 
    chat_id: int, 
    message: str, 
    **kwargs
) -> Dict[str, Any]:
    """Async implementation of notification retry."""
    try:
        notification_service = NotificationService()
        
        # Send the notification
        success = await notification_service.send_direct_message(
            chat_id=chat_id,
            message=message,
            parse_mode=kwargs.get("parse_mode", "Markdown"),
            reply_markup=kwargs.get("reply_markup"),
        )
        
        if success:
            return {
                "success": True,
                "notification_type": notification_type,
                "chat_id": chat_id,
                "sent_at": datetime.utcnow().isoformat()
            }
        else:
            raise Exception("Failed to send notification")
            
    except Exception as e:
        raise e


@retry_task(bind=True, max_retries=3, default_retry_delay=60)
def retry_meeting_resolution(self, meeting_id: int):
    """
    Retry failed meeting time slot resolution.
    
    Args:
        meeting_id: Meeting ID to resolve
    """
    try:
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_retry_meeting_resolution_async(meeting_id))
            return result
        finally:
            loop.close()
    except Exception as exc:
        delay = min(300, 60 * (2 ** self.request.retries))
        
        if self.request.retries >= self.max_retries:
            logger.error(
                f"Meeting resolution permanently failed for meeting {meeting_id}",
                extra={
                    "meeting_id": meeting_id,
                    "retries": self.request.retries,
                    "error": str(exc),
                }
            )
            raise MaxRetriesExceededError("Max retries exceeded for meeting resolution")
        
        raise self.retry(countdown=delay, exc=exc)


async def _retry_meeting_resolution_async(meeting_id: int) -> Dict[str, Any]:
    """Async implementation of meeting resolution retry."""
    async with get_db_session() as session:
        try:
            # Get meeting with participants
            meeting = await _get_meeting_with_participants(session, meeting_id)
            if not meeting:
                return {"success": False, "error": "Meeting not found"}
            
            # Use scheduler service to resolve time slots
            scheduler_service = SchedulerService()
            result = await scheduler_service.resolve_meeting_time_slots(meeting_id)
            
            if result["success"]:
                # Update meeting status
                meeting.status = "time_slots_resolved"
                await session.commit()
                
                # Notify participants
                await _notify_participants_about_resolution(meeting, result.get("time_slots", []))
            
            return result
            
        except Exception as e:
            await session.rollback()
            raise e


@retry_task(bind=True, max_retries=2, default_retry_delay=30)
def cleanup_failed_task(self, task_id: str, task_name: str, error_message: str):
    """
    Clean up after a permanently failed task.
    
    Args:
        task_id: Celery task ID
        task_name: Name of the failed task
        error_message: Error message from the failure
    """
    try:
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _cleanup_failed_task_async(task_id, task_name, error_message)
            )
            return result
        finally:
            loop.close()
    except Exception as exc:
        # Don't retry cleanup tasks - just log the error
        logger.error(
            f"Failed to cleanup task {task_id}: {exc}",
            extra={
                "task_id": task_id,
                "task_name": task_name,
                "original_error": error_message,
                "cleanup_error": str(exc),
            }
        )
        raise exc


async def _cleanup_failed_task_async(
    task_id: str, 
    task_name: str, 
    error_message: str
) -> Dict[str, Any]:
    """Async implementation of failed task cleanup."""
    try:
        # Log the permanent failure
        logger.error(
            f"Task {task_name} ({task_id}) permanently failed: {error_message}",
            extra={
                "task_id": task_id,
                "task_name": task_name,
                "error_message": error_message,
                "failed_at": datetime.utcnow().isoformat(),
            }
        )
        
        # Perform any necessary cleanup based on task type
        if "meeting" in task_name.lower():
            # Could update meeting status to failed, notify users, etc.
            pass
        elif "oauth" in task_name.lower():
            # Could clean up OAuth-related state
            pass
        
        return {
            "success": True,
            "task_id": task_id,
            "cleaned_up_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise e


# Helper functions

async def _get_meeting(session: AsyncSession, meeting_id: int) -> Optional[Meeting]:
    """Get meeting by ID."""
    query = select(Meeting).where(Meeting.id == meeting_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def _get_meeting_with_participants(session: AsyncSession, meeting_id: int) -> Optional[Meeting]:
    """Get meeting with participants loaded."""
    query = select(Meeting).where(Meeting.id == meeting_id)
    result = await session.execute(query)
    meeting = result.scalar_one_or_none()
    
    if meeting:
        # Load participants relationship
        await session.refresh(meeting, ["participants"])
    
    return meeting


async def _get_user_with_oauth(session: AsyncSession, user_id: int) -> Optional[User]:
    """Get user with OAuth token."""
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if user:
        # Load OAuth token relationship
        await session.refresh(user, ["oauth_token"])
    
    return user


async def _perform_calendar_operation(
    operation_type: str, 
    meeting: Meeting, 
    user: User, 
    **kwargs
) -> Dict[str, Any]:
    """Perform the specific calendar operation."""
    provider = GoogleCalendarProvider()
    
    if operation_type == "freebusy":
        return await provider.get_free_busy_times(
            user.oauth_token,
            kwargs.get("start_time"),
            kwargs.get("end_time"),
            kwargs.get("calendar_ids", [])
        )
    elif operation_type == "create_event":
        return await provider.create_calendar_event(
            user.oauth_token,
            meeting.title,
            kwargs.get("start_time"),
            kwargs.get("end_time"),
            kwargs.get("attendees", []),
            kwargs.get("description", ""),
            kwargs.get("location", "")
        )
    elif operation_type == "update_event":
        return await provider.update_calendar_event(
            user.oauth_token,
            kwargs.get("event_id"),
            kwargs.get("updates", {})
        )
    elif operation_type == "delete_event":
        return await provider.delete_calendar_event(
            user.oauth_token,
            kwargs.get("event_id")
        )
    else:
        return {"success": False, "error": f"Unknown operation type: {operation_type}"}


async def _update_meeting_status(session: AsyncSession, meeting_id: int, operation_type: str):
    """Update meeting status based on completed operation."""
    meeting = await _get_meeting(session, meeting_id)
    if not meeting:
        return
    
    if operation_type == "create_event":
        meeting.status = "confirmed"
    elif operation_type == "freebusy":
        meeting.status = "time_slots_resolved"


async def _notify_participants_about_resolution(meeting: Meeting, time_slots: List[Dict[str, Any]]):
    """Notify participants that time slots have been resolved."""
    notification_service = NotificationService()
    
    message = f"""
🎯 **Time Slots Ready!**

Meeting: *{meeting.title}*

I found {len(time_slots)} available time slots. Please vote for your preferred times!

Use the voting buttons below to cast your votes.
    """.strip()
    
    for participant in meeting.participants:
        if participant.status == "active":
            # Send notification asynchronously (don't wait for completion)
            retry_notification.delay(
                notification_type="time_slots_resolved",
                chat_id=participant.telegram_chat_id,
                message=message,
                meeting_id=meeting.id
            )
