"""Background job scheduler for periodic tasks.

Uses APScheduler to run price sync and cleanup jobs.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import delete, select

from src.core.config import get_settings
from src.core.database import AsyncSessionLocal
from src.models import PriceHistory
from src.services.price_sync import price_sync_service
from src.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class SchedulerService:
    """Service for managing background scheduled jobs."""

    def __init__(self):
        self._scheduler: AsyncIOScheduler | None = None
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> None:
        """Start the scheduler with configured jobs."""
        if self._scheduler is not None:
            logger.warning("Scheduler already running")
            return

        self._scheduler = AsyncIOScheduler()

        # Price sync job - runs every N hours
        self._scheduler.add_job(
            self._run_price_sync,
            trigger=IntervalTrigger(hours=settings.sync_prices_interval_hours),
            id="price_sync",
            name="Sync tour prices from Civitatis",
            replace_existing=True,
            max_instances=1,
        )

        # Cleanup job - runs daily at 3 AM
        self._scheduler.add_job(
            self._run_cleanup,
            trigger=CronTrigger(hour=3, minute=0),
            id="cleanup",
            name="Cleanup old price history records",
            replace_existing=True,
            max_instances=1,
        )

        self._scheduler.start()
        self._is_running = True

        logger.info(
            "Scheduler started",
            price_sync_interval_hours=settings.sync_prices_interval_hours,
            cleanup_days_to_keep=settings.cleanup_days_to_keep,
        )

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler is None:
            return

        self._scheduler.shutdown(wait=True)
        self._scheduler = None
        self._is_running = False

        logger.info("Scheduler stopped")

    async def _run_price_sync(self) -> None:
        """Execute the price sync job."""
        logger.info("Starting scheduled price sync")
        try:
            stats = await price_sync_service.sync_all_destinations()
            logger.info(
                "Scheduled price sync completed",
                tours_found=stats["total_tours_found"],
                price_changes=stats["total_price_changes"],
            )
        except Exception as e:
            logger.error(f"Scheduled price sync failed: {e}")

    async def _run_cleanup(self) -> None:
        """Execute the cleanup job to remove old price history."""
        logger.info("Starting scheduled cleanup")
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=settings.cleanup_days_to_keep
            )

            async with AsyncSessionLocal() as db:
                # Count records to delete
                count_query = select(PriceHistory.id).where(
                    PriceHistory.recorded_at < cutoff_date
                )
                result = await db.execute(count_query)
                count = len(result.all())

                if count > 0:
                    # Delete old records
                    await db.execute(
                        delete(PriceHistory).where(
                            PriceHistory.recorded_at < cutoff_date
                        )
                    )
                    await db.commit()

                    logger.info(
                        "Cleanup completed",
                        records_deleted=count,
                        cutoff_date=cutoff_date.isoformat(),
                    )
                else:
                    logger.info("No records to cleanup")

        except Exception as e:
            logger.error(f"Scheduled cleanup failed: {e}")

    def trigger_price_sync(self) -> None:
        """Manually trigger a price sync job."""
        if self._scheduler is None:
            logger.warning("Scheduler not running")
            return

        self._scheduler.add_job(
            self._run_price_sync,
            id="price_sync_manual",
            name="Manual price sync",
            replace_existing=True,
        )
        logger.info("Manual price sync triggered")

    def get_jobs_info(self) -> list[dict]:
        """Get information about scheduled jobs."""
        if self._scheduler is None:
            return []

        jobs = []
        for job in self._scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        return jobs


# Global scheduler instance
scheduler_service = SchedulerService()


async def run_initial_sync() -> None:
    """Run an initial price sync on startup if database is empty."""
    async with AsyncSessionLocal() as db:
        from src.models import Tour
        result = await db.execute(select(Tour.id).limit(1))
        if result.scalar_one_or_none() is None:
            logger.info("Database empty, running initial sync")
            await price_sync_service.sync_all_destinations()
