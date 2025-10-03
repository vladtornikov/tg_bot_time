"""Command line interface for worker management."""

import asyncio
import logging
import sys
from typing import List, Optional

import click
from celery import Celery
from celery.bin import worker, beat

from src.config.settings import get_settings
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Worker management CLI."""
    pass


@cli.command()
@click.option("--queues", "-Q", default="default", help="Comma-separated list of queues to consume")
@click.option("--concurrency", "-c", type=int, help="Number of worker processes")
@click.option("--loglevel", "-l", default="INFO", help="Log level")
@click.option("--hostname", "-n", help="Worker hostname")
def worker_cmd(queues: str, concurrency: Optional[int], loglevel: str, hostname: Optional[str]):
    """Start Celery worker."""
    settings = get_settings()
    
    # Parse queues
    queue_list = [q.strip() for q in queues.split(",")]
    
    # Set worker options
    worker_options = {
        "loglevel": loglevel,
        "queues": queue_list,
    }
    
    if concurrency:
        worker_options["concurrency"] = concurrency
    else:
        worker_options["concurrency"] = settings.worker_concurrency
    
    if hostname:
        worker_options["hostname"] = hostname
    
    # Start worker
    worker_instance = worker.worker(app=celery_app)
    worker_instance.run_from_argv(sys.argv)


@cli.command()
@click.option("--loglevel", "-l", default="INFO", help="Log level")
def beat_cmd(loglevel: str):
    """Start Celery beat scheduler."""
    beat_options = {
        "loglevel": loglevel,
    }
    
    # Start beat scheduler
    beat_instance = beat.beat(app=celery_app)
    beat_instance.run_from_argv(sys.argv)


@cli.command()
@click.option("--queue", "-Q", default="default", help="Queue to purge")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def purge(queue: str, confirm: bool):
    """Purge all messages from a queue."""
    if not confirm:
        if not click.confirm(f"Are you sure you want to purge queue '{queue}'?"):
            click.echo("Operation cancelled.")
            return
    
    try:
        celery_app.control.purge()
        click.echo(f"Successfully purged queue '{queue}'")
    except Exception as e:
        click.echo(f"Error purging queue: {e}", err=True)


@cli.command()
def status():
    """Show worker status."""
    try:
        inspect = celery_app.control.inspect()
        
        # Get active workers
        active = inspect.active()
        if active:
            click.echo("Active workers:")
            for worker_name, tasks in active.items():
                click.echo(f"  {worker_name}: {len(tasks)} active tasks")
        else:
            click.echo("No active workers found")
        
        # Get registered tasks
        registered = inspect.registered()
        if registered:
            click.echo("\nRegistered tasks:")
            for worker_name, tasks in registered.items():
                click.echo(f"  {worker_name}:")
                for task in sorted(tasks):
                    click.echo(f"    - {task}")
        
        # Get worker stats
        stats = inspect.stats()
        if stats:
            click.echo("\nWorker statistics:")
            for worker_name, worker_stats in stats.items():
                click.echo(f"  {worker_name}:")
                click.echo(f"    Total tasks: {worker_stats.get('total', 'N/A')}")
                click.echo(f"    Pool processes: {worker_stats.get('pool', {}).get('processes', 'N/A')}")
                
    except Exception as e:
        click.echo(f"Error getting status: {e}", err=True)


@cli.command()
@click.option("--task", "-t", help="Task name to revoke")
@click.option("--terminate", is_flag=True, help="Terminate running tasks")
def revoke(task: Optional[str], terminate: bool):
    """Revoke tasks."""
    if not task:
        click.echo("Please specify a task name with --task")
        return
    
    try:
        celery_app.control.revoke(task, terminate=terminate)
        action = "terminated" if terminate else "revoked"
        click.echo(f"Successfully {action} task '{task}'")
    except Exception as e:
        click.echo(f"Error revoking task: {e}", err=True)


@cli.command()
@click.option("--task", "-t", required=True, help="Task name to call")
@click.option("--args", "-a", help="Task arguments (JSON format)")
@click.option("--kwargs", "-k", help="Task keyword arguments (JSON format)")
@click.option("--queue", "-Q", help="Queue to send task to")
@click.option("--async", "async_mode", is_flag=True, help="Send task asynchronously")
def call(task: str, args: Optional[str], kwargs: Optional[str], queue: Optional[str], async_mode: bool):
    """Call a task directly."""
    import json
    
    try:
        # Parse arguments
        task_args = []
        if args:
            task_args = json.loads(args)
        
        task_kwargs = {}
        if kwargs:
            task_kwargs = json.loads(kwargs)
        
        # Get task function
        task_func = celery_app.tasks.get(task)
        if not task_func:
            click.echo(f"Task '{task}' not found", err=True)
            return
        
        # Send task
        if async_mode:
            result = task_func.apply_async(args=task_args, kwargs=task_kwargs, queue=queue)
            click.echo(f"Task sent with ID: {result.id}")
        else:
            result = task_func.apply(args=task_args, kwargs=task_kwargs, queue=queue)
            click.echo(f"Task result: {result}")
            
    except json.JSONDecodeError as e:
        click.echo(f"Error parsing JSON: {e}", err=True)
    except Exception as e:
        click.echo(f"Error calling task: {e}", err=True)


@cli.command()
def health():
    """Check worker health."""
    try:
        inspect = celery_app.control.inspect()
        
        # Check if workers are responding
        ping_result = inspect.ping()
        if not ping_result:
            click.echo("❌ No workers responding", err=True)
            return 1
        
        click.echo("✅ Workers are responding")
        
        # Check active tasks
        active = inspect.active()
        total_active = sum(len(tasks) for tasks in active.values())
        click.echo(f"📊 Total active tasks: {total_active}")
        
        # Check registered tasks
        registered = inspect.registered()
        if registered:
            total_tasks = len(set().union(*registered.values()))
            click.echo(f"📋 Total registered tasks: {total_tasks}")
        
        return 0
        
    except Exception as e:
        click.echo(f"❌ Health check failed: {e}", err=True)
        return 1


if __name__ == "__main__":
    cli()
