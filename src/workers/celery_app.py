"""Celery application configuration and setup."""

import logging
from typing import Any, Dict

from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
from celery.utils.log import get_task_logger

from src.config.settings import get_settings

logger = get_task_logger(__name__)


def create_celery_app() -> Celery:
    """Create and configure Celery application."""
    settings = get_settings()
    
    # Create Celery app
    app = Celery(
        "tg_bot",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=[
            "src.workers.oauth_reminders",
            "src.workers.retry_tasks",
            "src.workers.scheduled_tasks",
        ]
    )
    
    # Configure Celery
    app.conf.update(
        # Task settings
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        
        # Worker settings
        worker_concurrency=settings.worker_concurrency,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
        
        # Task routing
        task_routes={
            "src.workers.oauth_reminders.*": {"queue": "oauth"},
            "src.workers.retry_tasks.*": {"queue": "retry"},
            "src.workers.scheduled_tasks.*": {"queue": "scheduled"},
        },
        
        # Task execution settings
        task_acks_late=True,
        worker_disable_rate_limits=True,
        
        # Result backend settings
        result_expires=3600,  # 1 hour
        result_backend_transport_options={
            "master_name": "mymaster",
            "visibility_timeout": 3600,
        },
        
        # Retry settings
        task_default_retry_delay=60,  # 1 minute
        task_max_retries=3,
        
        # Beat scheduler settings (for periodic tasks)
        beat_schedule={
            "cleanup-expired-tokens": {
                "task": "src.workers.scheduled_tasks.cleanup_expired_tokens",
                "schedule": 3600.0,  # Run every hour
            },
            "cleanup-completed-meetings": {
                "task": "src.workers.scheduled_tasks.cleanup_completed_meetings",
                "schedule": 86400.0,  # Run daily
            },
            "send-oauth-reminders": {
                "task": "src.workers.scheduled_tasks.send_oauth_reminders",
                "schedule": 7200.0,  # Run every 2 hours
            },
        },
        
        # Logging
        worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
        worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
    )
    
    # Set up logging
    if settings.is_development:
        app.conf.update(
            task_always_eager=False,
            task_eager_propagates=True,
        )
    
    return app


# Create the Celery app instance
celery_app = create_celery_app()


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Log task start."""
    logger.info(
        f"Starting task {task.name}",
        extra={
            "task_id": task_id,
            "task_name": task.name,
            "args": args,
            "kwargs": kwargs,
        }
    )


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Log task completion."""
    logger.info(
        f"Completed task {task.name}",
        extra={
            "task_id": task_id,
            "task_name": task.name,
            "state": state,
            "result": retval,
        }
    )


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Log task failure."""
    logger.error(
        f"Task {sender.name} failed: {exception}",
        extra={
            "task_id": task_id,
            "task_name": sender.name,
            "exception": str(exception),
            "traceback": traceback,
            "einfo": str(einfo),
        }
    )


# Task decorators for different queues
def oauth_task(*args, **kwargs):
    """Decorator for OAuth-related tasks."""
    kwargs.setdefault("queue", "oauth")
    kwargs.setdefault("routing_key", "oauth")
    return celery_app.task(*args, **kwargs)


def retry_task(*args, **kwargs):
    """Decorator for retry tasks."""
    kwargs.setdefault("queue", "retry")
    kwargs.setdefault("routing_key", "retry")
    return celery_app.task(*args, **kwargs)


def scheduled_task(*args, **kwargs):
    """Decorator for scheduled tasks."""
    kwargs.setdefault("queue", "scheduled")
    kwargs.setdefault("routing_key", "scheduled")
    return celery_app.task(*args, **kwargs)


def general_task(*args, **kwargs):
    """Decorator for general tasks."""
    return celery_app.task(*args, **kwargs)
