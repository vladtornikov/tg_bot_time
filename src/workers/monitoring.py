"""Worker monitoring and metrics collection."""

import logging
import time
from typing import Dict, Any, List

from celery import Celery
from celery.events.state import State
from celery.signals import task_prerun, task_postrun, task_failure, worker_ready, worker_shutdown

from src.config.settings import get_settings
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


class WorkerMonitor:
    """Monitor worker performance and health."""
    
    def __init__(self):
        self.settings = get_settings()
        self.state = State()
        self.task_stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "retried_tasks": 0,
            "task_times": {},
            "queue_sizes": {},
        }
    
    def start_monitoring(self):
        """Start monitoring worker events."""
        # Connect to event signals
        task_prerun.connect(self.on_task_prerun)
        task_postrun.connect(self.on_task_postrun)
        task_failure.connect(self.on_task_failure)
        worker_ready.connect(self.on_worker_ready)
        worker_shutdown.connect(self.on_worker_shutdown)
        
        logger.info("Worker monitoring started")
    
    def on_task_prerun(self, sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
        """Handle task start event."""
        self.task_stats["total_tasks"] += 1
        self.task_stats["task_times"][task_id] = time.time()
        
        logger.debug(
            f"Task {task.name} started",
            extra={
                "task_id": task_id,
                "task_name": task.name,
                "queue": kwargs.get("queue", "default"),
            }
        )
    
    def on_task_postrun(self, sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
        """Handle task completion event."""
        if task_id in self.task_stats["task_times"]:
            execution_time = time.time() - self.task_stats["task_times"][task_id]
            del self.task_stats["task_times"][task_id]
            
            # Track task execution time
            task_name = task.name
            if task_name not in self.task_stats["task_times"]:
                self.task_stats["task_times"][task_name] = []
            self.task_stats["task_times"][task_name].append(execution_time)
        
        if state == "SUCCESS":
            self.task_stats["successful_tasks"] += 1
        elif state == "RETRY":
            self.task_stats["retried_tasks"] += 1
        
        logger.debug(
            f"Task {task.name} completed with state {state}",
            extra={
                "task_id": task_id,
                "task_name": task.name,
                "state": state,
                "execution_time": execution_time if task_id in self.task_stats["task_times"] else None,
            }
        )
    
    def on_task_failure(self, sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
        """Handle task failure event."""
        self.task_stats["failed_tasks"] += 1
        
        logger.error(
            f"Task {sender.name} failed: {exception}",
            extra={
                "task_id": task_id,
                "task_name": sender.name,
                "exception": str(exception),
                "traceback": traceback,
            }
        )
    
    def on_worker_ready(self, sender=None, **kwargs):
        """Handle worker ready event."""
        logger.info(f"Worker {sender} is ready")
    
    def on_worker_shutdown(self, sender=None, **kwargs):
        """Handle worker shutdown event."""
        logger.info(f"Worker {sender} is shutting down")
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get current worker statistics."""
        inspect = celery_app.control.inspect()
        
        # Get active tasks
        active = inspect.active()
        total_active = sum(len(tasks) for tasks in (active or {}).values())
        
        # Get registered tasks
        registered = inspect.registered()
        total_registered = len(set().union(*registered.values())) if registered else 0
        
        # Get worker stats
        stats = inspect.stats()
        
        return {
            "active_tasks": total_active,
            "registered_tasks": total_registered,
            "worker_count": len(stats) if stats else 0,
            "task_statistics": self.task_stats,
            "worker_stats": stats,
        }
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status information."""
        inspect = celery_app.control.inspect()
        
        # Get scheduled tasks
        scheduled = inspect.scheduled()
        
        # Get reserved tasks
        reserved = inspect.reserved()
        
        queue_info = {}
        
        if scheduled:
            for worker, tasks in scheduled.items():
                queue_info[worker] = {
                    "scheduled": len(tasks),
                    "scheduled_tasks": tasks,
                }
        
        if reserved:
            for worker, tasks in reserved.items():
                if worker in queue_info:
                    queue_info[worker]["reserved"] = len(tasks)
                    queue_info[worker]["reserved_tasks"] = tasks
                else:
                    queue_info[worker] = {
                        "reserved": len(tasks),
                        "reserved_tasks": tasks,
                    }
        
        return queue_info
    
    def health_check(self) -> Dict[str, Any]:
        """Perform worker health check."""
        try:
            # Check if workers are responding
            inspect = celery_app.control.inspect()
            ping_result = inspect.ping()
            
            if not ping_result:
                return {
                    "status": "unhealthy",
                    "error": "No workers responding",
                    "timestamp": time.time(),
                }
            
            # Check queue sizes
            queue_status = self.get_queue_status()
            total_queued = sum(
                info.get("scheduled", 0) + info.get("reserved", 0)
                for info in queue_status.values()
            )
            
            # Check if queues are getting too large
            max_queue_size = 1000  # Configurable threshold
            if total_queued > max_queue_size:
                return {
                    "status": "degraded",
                    "warning": f"Queue size ({total_queued}) exceeds threshold ({max_queue_size})",
                    "queue_size": total_queued,
                    "timestamp": time.time(),
                }
            
            # Get worker stats
            worker_stats = self.get_worker_stats()
            
            return {
                "status": "healthy",
                "worker_count": worker_stats["worker_count"],
                "active_tasks": worker_stats["active_tasks"],
                "queue_size": total_queued,
                "timestamp": time.time(),
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time(),
            }


# Global monitor instance
monitor = WorkerMonitor()


def get_worker_monitor() -> WorkerMonitor:
    """Get the global worker monitor instance."""
    return monitor


def start_worker_monitoring():
    """Start worker monitoring."""
    monitor.start_monitoring()


def get_worker_health() -> Dict[str, Any]:
    """Get worker health status."""
    return monitor.health_check()


def get_worker_metrics() -> Dict[str, Any]:
    """Get worker metrics."""
    return {
        "stats": monitor.get_worker_stats(),
        "queue_status": monitor.get_queue_status(),
        "health": monitor.health_check(),
    }


# Prometheus metrics integration
try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    
    # Metrics
    task_counter = Counter(
        'celery_tasks_total',
        'Total number of tasks processed',
        ['task_name', 'status']
    )
    
    task_duration = Histogram(
        'celery_task_duration_seconds',
        'Task execution duration',
        ['task_name']
    )
    
    active_tasks_gauge = Gauge(
        'celery_active_tasks',
        'Number of active tasks'
    )
    
    queue_size_gauge = Gauge(
        'celery_queue_size',
        'Number of tasks in queue',
        ['queue_name']
    )
    
    def update_prometheus_metrics():
        """Update Prometheus metrics."""
        try:
            # Update task counters
            stats = monitor.get_worker_stats()
            task_counter.labels(
                task_name='all',
                status='total'
            )._value._value = stats["task_statistics"]["total_tasks"]
            
            task_counter.labels(
                task_name='all',
                status='successful'
            )._value._value = stats["task_statistics"]["successful_tasks"]
            
            task_counter.labels(
                task_name='all',
                status='failed'
            )._value._value = stats["task_statistics"]["failed_tasks"]
            
            # Update active tasks gauge
            active_tasks_gauge.set(stats["active_tasks"])
            
            # Update queue size gauges
            queue_status = monitor.get_queue_status()
            for worker, info in queue_status.items():
                queue_size_gauge.labels(queue_name=worker).set(
                    info.get("scheduled", 0) + info.get("reserved", 0)
                )
                
        except Exception as e:
            logger.error(f"Failed to update Prometheus metrics: {e}")
    
    def start_prometheus_server():
        """Start Prometheus metrics server."""
        try:
            start_http_server(9091)  # Different port from main Prometheus
            logger.info("Prometheus metrics server started on port 9091")
        except Exception as e:
            logger.error(f"Failed to start Prometheus server: {e}")

except ImportError:
    # Prometheus client not available
    def update_prometheus_metrics():
        pass
    
    def start_prometheus_server():
        pass
