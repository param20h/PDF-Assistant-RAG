"""Application background scheduler."""
import logging

from app.config import get_settings
from app.services.drive_sync import sync_drive_pdfs_with_session

logger = logging.getLogger(__name__)
settings = get_settings()
_scheduler = None


def start_scheduler():
    """Start recurring backend jobs."""
    global _scheduler

    if _scheduler and _scheduler.running:
        return _scheduler

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        if settings.DRIVE_SYNC_ENABLED:
            logger.warning("Drive PDF sync enabled but APScheduler is not installed")
        return None

    _scheduler = BackgroundScheduler(timezone="UTC")

    if settings.DRIVE_SYNC_ENABLED:
        _scheduler.add_job(
            sync_drive_pdfs_with_session,
            trigger=IntervalTrigger(minutes=settings.DRIVE_SYNC_INTERVAL_MINUTES),
            id="drive_pdf_sync",
            name="Hourly Google Drive PDF sync",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )
        logger.info(
            "Drive PDF sync scheduled every %s minutes",
            settings.DRIVE_SYNC_INTERVAL_MINUTES,
        )
    else:
        logger.info("Drive PDF sync disabled")

    # Document processing recovery — every 5 minutes
    try:
        from app.services.cleanup import cleanup_stale_documents, cleanup_old_deleted_documents

        _scheduler.add_job(
            cleanup_stale_documents,
            trigger=IntervalTrigger(minutes=5),
            id="recover_stale_processing",
            name="Recover documents stuck in processing",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60,
        )
        logger.info("Stale document recovery scheduled every 5 minutes")

        _scheduler.add_job(
            cleanup_old_deleted_documents,
            trigger=IntervalTrigger(days=1),
            id="cleanup_old_deleted",
            name="Purge old soft-deleted documents",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=300,
        )
        logger.info("Old deleted document cleanup scheduled daily")
    except Exception as e:
        logger.warning("Could not schedule cleanup jobs: %s", e)

    _scheduler.start()
    return _scheduler


def stop_scheduler():
    """Stop recurring backend jobs."""
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
    _scheduler = None
