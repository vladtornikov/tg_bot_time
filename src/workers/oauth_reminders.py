"""OAuth consent reminder tasks."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

from celery.exceptions import Retry
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db_session
from src.models.oauth import OAuthToken
from src.models.user import User
from src.services.notification import NotificationService
from src.workers.celery_app import oauth_task, celery_app


@oauth_task(bind=True, max_retries=3, default_retry_delay=300)
def send_oauth_reminder(self, user_id: int, telegram_chat_id: int, reminder_type: str = "consent"):
    """
    Send OAuth consent reminder to user.
    
    Args:
        user_id: User ID in the database
        telegram_chat_id: Telegram chat ID
        reminder_type: Type of reminder (consent, refresh, etc.)
    """
    try:
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _send_oauth_reminder_async(user_id, telegram_chat_id, reminder_type)
            )
            return result
        finally:
            loop.close()
    except Exception as exc:
        # Log the error and retry
        self.retry(countdown=60 * (self.request.retries + 1), exc=exc)


async def _send_oauth_reminder_async(user_id: int, telegram_chat_id: int, reminder_type: str) -> dict:
    """Async implementation of OAuth reminder sending."""
    async with get_db_session() as session:
        try:
            # Get user and OAuth token info
            user = await _get_user_with_oauth_status(session, user_id)
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Check if user already has valid OAuth token
            if user.oauth_token and user.oauth_token.is_valid():
                return {"success": False, "error": "User already has valid OAuth token"}
            
            # Send appropriate reminder message
            notification_service = NotificationService()
            
            if reminder_type == "consent":
                message = _get_consent_reminder_message()
            elif reminder_type == "refresh":
                message = _get_refresh_reminder_message()
            else:
                message = _get_general_reminder_message()
            
            # Send the reminder
            success = await notification_service.send_direct_message(
                chat_id=telegram_chat_id,
                message=message,
                parse_mode="Markdown"
            )
            
            if success:
                # Update reminder tracking
                await _update_reminder_tracking(session, user_id, reminder_type)
                await session.commit()
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "reminder_type": reminder_type,
                    "sent_at": datetime.utcnow().isoformat()
                }
            else:
                return {"success": False, "error": "Failed to send message"}
                
        except Exception as e:
            await session.rollback()
            raise e


@oauth_task(bind=True, max_retries=3, default_retry_delay=300)
def schedule_oauth_reminders(self, meeting_id: int):
    """
    Schedule OAuth reminders for meeting participants who need to consent.
    
    Args:
        meeting_id: Meeting ID to check for participants
    """
    try:
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_schedule_oauth_reminders_async(meeting_id))
            return result
        finally:
            loop.close()
    except Exception as exc:
        self.retry(countdown=60 * (self.request.retries + 1), exc=exc)


async def _schedule_oauth_reminders_async(meeting_id: int) -> dict:
    """Async implementation of OAuth reminder scheduling."""
    async with get_db_session() as session:
        try:
            # Get meeting participants who need OAuth consent
            participants_needing_consent = await _get_participants_needing_consent(
                session, meeting_id
            )
            
            scheduled_reminders = []
            
            for participant in participants_needing_consent:
                # Schedule immediate reminder
                task = send_oauth_reminder.apply_async(
                    args=[participant.user_id, participant.telegram_chat_id, "consent"],
                    countdown=0  # Send immediately
                )
                
                # Schedule follow-up reminder in 24 hours if no consent
                follow_up_task = send_oauth_reminder.apply_async(
                    args=[participant.user_id, participant.telegram_chat_id, "consent"],
                    countdown=86400  # 24 hours
                )
                
                scheduled_reminders.append({
                    "user_id": participant.user_id,
                    "telegram_chat_id": participant.telegram_chat_id,
                    "immediate_task_id": task.id,
                    "follow_up_task_id": follow_up_task.id,
                })
            
            return {
                "success": True,
                "meeting_id": meeting_id,
                "scheduled_count": len(scheduled_reminders),
                "reminders": scheduled_reminders,
                "scheduled_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            await session.rollback()
            raise e


@oauth_task(bind=True, max_retries=3, default_retry_delay=300)
def cancel_oauth_reminders(self, user_id: int, meeting_id: Optional[int] = None):
    """
    Cancel pending OAuth reminders for a user.
    
    Args:
        user_id: User ID to cancel reminders for
        meeting_id: Optional meeting ID to cancel reminders for specific meeting
    """
    try:
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _cancel_oauth_reminders_async(user_id, meeting_id)
            )
            return result
        finally:
            loop.close()
    except Exception as exc:
        self.retry(countdown=60 * (self.request.retries + 1), exc=exc)


async def _cancel_oauth_reminders_async(user_id: int, meeting_id: Optional[int]) -> dict:
    """Async implementation of OAuth reminder cancellation."""
    try:
        # Get active tasks for this user
        active_tasks = celery_app.control.inspect().active()
        
        cancelled_tasks = []
        
        if active_tasks:
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    if (task.get("name") == "src.workers.oauth_reminders.send_oauth_reminder" and
                        user_id in task.get("args", [])):
                        
                        # Revoke the task
                        celery_app.control.revoke(task["id"], terminate=True)
                        cancelled_tasks.append(task["id"])
        
        return {
            "success": True,
            "user_id": user_id,
            "meeting_id": meeting_id,
            "cancelled_tasks": cancelled_tasks,
            "cancelled_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise e


# Helper functions

async def _get_user_with_oauth_status(session: AsyncSession, user_id: int) -> Optional[User]:
    """Get user with OAuth token status."""
    from src.models.meeting import MeetingParticipant
    
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    
    if user:
        # Load OAuth token relationship
        await session.refresh(user, ["oauth_token"])
    
    return user


async def _get_participants_needing_consent(session: AsyncSession, meeting_id: int) -> List[dict]:
    """Get meeting participants who need OAuth consent."""
    from src.models.meeting import MeetingParticipant
    
    # Get participants who don't have valid OAuth tokens
    query = (
        select(MeetingParticipant)
        .join(User, MeetingParticipant.user_id == User.id)
        .outerjoin(OAuthToken, User.id == OAuthToken.user_id)
        .where(
            and_(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.status == "active",
                # User doesn't have OAuth token or token is invalid
                (OAuthToken.id.is_(None)) | (OAuthToken.expires_at < datetime.utcnow())
            )
        )
    )
    
    result = await session.execute(query)
    participants = result.scalars().all()
    
    return [
        {
            "user_id": p.user_id,
            "telegram_chat_id": p.telegram_chat_id,
            "username": p.username,
        }
        for p in participants
    ]


async def _update_reminder_tracking(session: AsyncSession, user_id: int, reminder_type: str):
    """Update reminder tracking information."""
    # This could be implemented as a separate model for tracking reminders
    # For now, we'll just log it
    pass


def _get_consent_reminder_message() -> str:
    """Get OAuth consent reminder message."""
    return """
🔐 **Calendar Access Required**

To schedule meetings, I need access to your Google Calendar. This helps me find the best time slots for everyone.

Please use `/link_calendar` to grant access.

*This reminder will be sent again in 24 hours if you haven't connected your calendar.*
    """.strip()


def _get_refresh_reminder_message() -> str:
    """Get OAuth refresh reminder message."""
    return """
🔄 **Calendar Access Expired**

Your calendar access has expired. To continue scheduling meetings, please reconnect your calendar.

Use `/link_calendar` to refresh your access.

*This reminder will be sent again in 24 hours if you haven't reconnected.*
    """.strip()


def _get_general_reminder_message() -> str:
    """Get general OAuth reminder message."""
    return """
📅 **Calendar Integration Needed**

To use the meeting scheduler, please connect your Google Calendar.

Use `/link_calendar` to get started.
    """.strip()
