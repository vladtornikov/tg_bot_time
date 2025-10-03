"""Scheduled tasks for periodic maintenance and cleanup."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy import select, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db_session
from src.models.meeting import Meeting, MeetingParticipant
from src.models.oauth import OAuthToken
from src.models.user import User
from src.models.vote import Vote
from src.services.notification import NotificationService
from src.workers.celery_app import scheduled_task, celery_app

logger = logging.getLogger(__name__)


@scheduled_task
def cleanup_expired_tokens():
    """Clean up expired OAuth tokens and related data."""
    try:
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_cleanup_expired_tokens_async())
            return result
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Failed to cleanup expired tokens: {exc}")
        raise exc


async def _cleanup_expired_tokens_async() -> Dict[str, Any]:
    """Async implementation of expired token cleanup."""
    async with get_db_session() as session:
        try:
            # Find expired tokens (expired more than 7 days ago)
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            # Get expired tokens
            expired_tokens_query = select(OAuthToken).where(
                and_(
                    OAuthToken.expires_at < cutoff_date,
                    OAuthToken.deleted_at.is_(None)
                )
            )
            result = await session.execute(expired_tokens_query)
            expired_tokens = result.scalars().all()
            
            deleted_count = 0
            for token in expired_tokens:
                # Soft delete the token
                token.deleted_at = datetime.utcnow()
                deleted_count += 1
            
            # Also clean up tokens that are close to expiration (within 1 day)
            # and haven't been used recently (no meetings created in last 30 days)
            near_expiry_date = datetime.utcnow() + timedelta(days=1)
            last_used_cutoff = datetime.utcnow() - timedelta(days=30)
            
            # Find unused tokens near expiration
            unused_tokens_query = (
                select(OAuthToken)
                .join(User, OAuthToken.user_id == User.id)
                .where(
                    and_(
                        OAuthToken.expires_at < near_expiry_date,
                        OAuthToken.expires_at > datetime.utcnow(),  # Still valid
                        or_(
                            User.last_meeting_created_at.is_(None),
                            User.last_meeting_created_at < last_used_cutoff
                        ),
                        OAuthToken.deleted_at.is_(None)
                    )
                )
            )
            result = await session.execute(unused_tokens_query)
            unused_tokens = result.scalars().all()
            
            for token in unused_tokens:
                token.deleted_at = datetime.utcnow()
                deleted_count += 1
            
            await session.commit()
            
            logger.info(
                f"Cleaned up {deleted_count} expired/unused OAuth tokens",
                extra={
                    "expired_tokens": len(expired_tokens),
                    "unused_tokens": len(unused_tokens),
                    "total_deleted": deleted_count,
                    "cleanup_date": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "expired_tokens": len(expired_tokens),
                "unused_tokens": len(unused_tokens),
                "cleanup_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            await session.rollback()
            raise e


@scheduled_task
def cleanup_completed_meetings():
    """Clean up old completed meetings and related data."""
    try:
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_cleanup_completed_meetings_async())
            return result
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Failed to cleanup completed meetings: {exc}")
        raise exc


async def _cleanup_completed_meetings_async() -> Dict[str, Any]:
    """Async implementation of completed meetings cleanup."""
    async with get_db_session() as session:
        try:
            # Find meetings that were completed more than 30 days ago
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            # Get completed meetings
            completed_meetings_query = select(Meeting).where(
                and_(
                    Meeting.status.in_(["confirmed", "completed", "cancelled"]),
                    Meeting.updated_at < cutoff_date,
                    Meeting.deleted_at.is_(None)
                )
            )
            result = await session.execute(completed_meetings_query)
            completed_meetings = result.scalars().all()
            
            deleted_count = 0
            for meeting in completed_meetings:
                # Soft delete the meeting and related data
                meeting.deleted_at = datetime.utcnow()
                
                # Soft delete related votes
                for participant in meeting.participants:
                    for vote in participant.votes:
                        vote.deleted_at = datetime.utcnow()
                
                deleted_count += 1
            
            await session.commit()
            
            logger.info(
                f"Cleaned up {deleted_count} old completed meetings",
                extra={
                    "deleted_count": deleted_count,
                    "cutoff_date": cutoff_date.isoformat(),
                    "cleanup_date": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
                "cleanup_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            await session.rollback()
            raise e


@scheduled_task
def send_oauth_reminders():
    """Send OAuth consent reminders to users who need them."""
    try:
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_send_oauth_reminders_async())
            return result
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Failed to send OAuth reminders: {exc}")
        raise exc


async def _send_oauth_reminders_async() -> Dict[str, Any]:
    """Async implementation of OAuth reminder sending."""
    async with get_db_session() as session:
        try:
            # Find users who need OAuth consent reminders
            users_needing_reminders = await _get_users_needing_oauth_reminders(session)
            
            reminder_count = 0
            for user_data in users_needing_reminders:
                # Schedule OAuth reminder task
                from src.workers.oauth_reminders import send_oauth_reminder
                
                send_oauth_reminder.delay(
                    user_id=user_data["user_id"],
                    telegram_chat_id=user_data["telegram_chat_id"],
                    reminder_type="consent"
                )
                
                reminder_count += 1
            
            logger.info(
                f"Scheduled {reminder_count} OAuth consent reminders",
                extra={
                    "reminder_count": reminder_count,
                    "scheduled_date": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "success": True,
                "reminder_count": reminder_count,
                "scheduled_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            await session.rollback()
            raise e


@scheduled_task
def cleanup_abandoned_meetings():
    """Clean up meetings that were created but never progressed."""
    try:
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_cleanup_abandoned_meetings_async())
            return result
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Failed to cleanup abandoned meetings: {exc}")
        raise exc


async def _cleanup_abandoned_meetings_async() -> Dict[str, Any]:
    """Async implementation of abandoned meetings cleanup."""
    async with get_db_session() as session:
        try:
            # Find meetings that were created but never progressed beyond initial state
            # More than 7 days ago
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            abandoned_meetings_query = select(Meeting).where(
                and_(
                    Meeting.status == "created",
                    Meeting.created_at < cutoff_date,
                    Meeting.deleted_at.is_(None)
                )
            )
            result = await session.execute(abandoned_meetings_query)
            abandoned_meetings = result.scalars().all()
            
            deleted_count = 0
            for meeting in abandoned_meetings:
                # Soft delete the meeting
                meeting.deleted_at = datetime.utcnow()
                meeting.status = "abandoned"
                deleted_count += 1
            
            await session.commit()
            
            logger.info(
                f"Cleaned up {deleted_count} abandoned meetings",
                extra={
                    "deleted_count": deleted_count,
                    "cutoff_date": cutoff_date.isoformat(),
                    "cleanup_date": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_date.isoformat(),
                "cleanup_date": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            await session.rollback()
            raise e


@scheduled_task
def generate_usage_statistics():
    """Generate usage statistics for monitoring and analytics."""
    try:
        # Run the async function in the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_generate_usage_statistics_async())
            return result
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Failed to generate usage statistics: {exc}")
        raise exc


async def _generate_usage_statistics_async() -> Dict[str, Any]:
    """Async implementation of usage statistics generation."""
    async with get_db_session() as session:
        try:
            # Calculate statistics for the last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            # Count active users
            active_users_query = select(User).where(User.last_active_at > yesterday)
            result = await session.execute(active_users_query)
            active_users_count = len(result.scalars().all())
            
            # Count meetings created
            meetings_created_query = select(Meeting).where(Meeting.created_at > yesterday)
            result = await session.execute(meetings_created_query)
            meetings_created_count = len(result.scalars().all())
            
            # Count meetings completed
            meetings_completed_query = select(Meeting).where(
                and_(
                    Meeting.status == "confirmed",
                    Meeting.updated_at > yesterday
                )
            )
            result = await session.execute(meetings_completed_query)
            meetings_completed_count = len(result.scalars().all())
            
            # Count OAuth tokens
            oauth_tokens_query = select(OAuthToken).where(
                and_(
                    OAuthToken.expires_at > datetime.utcnow(),
                    OAuthToken.deleted_at.is_(None)
                )
            )
            result = await session.execute(oauth_tokens_query)
            active_oauth_tokens_count = len(result.scalars().all())
            
            statistics = {
                "active_users_24h": active_users_count,
                "meetings_created_24h": meetings_created_count,
                "meetings_completed_24h": meetings_completed_count,
                "active_oauth_tokens": active_oauth_tokens_count,
                "generated_at": datetime.utcnow().isoformat(),
                "period": "24h"
            }
            
            logger.info(
                "Generated usage statistics",
                extra=statistics
            )
            
            return {
                "success": True,
                "statistics": statistics
            }
            
        except Exception as e:
            await session.rollback()
            raise e


# Helper functions

async def _get_users_needing_oauth_reminders(session: AsyncSession) -> List[Dict[str, Any]]:
    """Get users who need OAuth consent reminders."""
    # Find users who don't have OAuth tokens or have expired tokens
    # and haven't been reminded in the last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    
    users_query = (
        select(User)
        .outerjoin(OAuthToken, User.id == OAuthToken.user_id)
        .where(
            and_(
                User.deleted_at.is_(None),
                # No OAuth token or token is expired
                or_(
                    OAuthToken.id.is_(None),
                    OAuthToken.expires_at < datetime.utcnow()
                ),
                # Haven't been reminded recently (this would need a reminder tracking table)
                # For now, just check users who are active but don't have valid tokens
                User.last_active_at > yesterday
            )
        )
    )
    
    result = await session.execute(users_query)
    users = result.scalars().all()
    
    return [
        {
            "user_id": user.id,
            "telegram_chat_id": user.telegram_id,
            "username": user.username,
        }
        for user in users
    ]
