"""
Scheduler Service — Runs periodic background tasks.

Uses APScheduler for in-process scheduling. This is the simplest solution
compatible with the current SQLite-based architecture.

Tasks:
- Inactivity monitoring (daily at 2 AM UTC)
"""
import logging
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from ..database import SessionLocal
from .inactivity_monitor import run_inactivity_monitor

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[BackgroundScheduler] = None


def inactivity_monitor_job():
    """Scheduled job: run inactivity monitoring."""
    logger.info("Starting inactivity monitoring job")
    db = SessionLocal()
    try:
        summary = run_inactivity_monitor(db)
        logger.info(f"Inactivity monitoring completed: {summary}")
    except Exception as e:
        logger.error(f"Inactivity monitoring job failed: {e}", exc_info=True)
    finally:
        db.close()


def job_listener(event):
    """Listener for scheduler events."""
    if event.exception:
        logger.error(f"Job {event.job_id} failed: {event.exception}", exc_info=True)
    else:
        logger.info(f"Job {event.job_id} executed successfully")


def start_scheduler():
    """Start the background scheduler."""
    global scheduler

    if scheduler is not None and scheduler.running:
        logger.warning("Scheduler already running")
        return

    scheduler = BackgroundScheduler(daemon=True)

    # Add inactivity monitoring job (daily at 2 AM UTC)
    scheduler.add_job(
        inactivity_monitor_job,
        trigger=CronTrigger(hour=2, minute=0, timezone='UTC'),
        id="inactivity_monitor",
        name="Inactivity Monitoring",
        replace_existing=True,
    )

    # Add event listener
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    scheduler.start()
    logger.info("Scheduler started with inactivity monitoring job (daily at 2 AM UTC)")


def stop_scheduler():
    """Stop the background scheduler."""
    global scheduler

    if scheduler is not None and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


def get_scheduler_status() -> dict:
    """Get scheduler status information."""
    global scheduler

    if scheduler is None:
        return {"running": False, "jobs": []}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        })

    return {
        "running": scheduler.running,
        "jobs": jobs,
    }
