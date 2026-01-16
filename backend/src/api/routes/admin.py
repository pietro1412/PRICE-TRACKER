"""Admin routes for system management."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from src.api.dependencies import get_current_superuser
from src.models import User
from src.services import price_sync_service, scheduler_service

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/scheduler/status")
async def get_scheduler_status(
    current_user: User = Depends(get_current_superuser),
) -> dict:
    """Get scheduler status and job information."""
    return {
        "is_running": scheduler_service.is_running,
        "jobs": scheduler_service.get_jobs_info(),
    }


@router.post("/sync/trigger")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_superuser),
    destination: str | None = None,
) -> dict:
    """Manually trigger a price sync job."""
    if not scheduler_service.is_running:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler is not running",
        )

    if destination:
        # Sync specific destination
        background_tasks.add_task(
            _sync_destination,
            destination,
        )
        return {
            "status": "started",
            "message": f"Sync triggered for destination: {destination}",
        }
    else:
        # Sync all destinations
        scheduler_service.trigger_price_sync()
        return {
            "status": "started",
            "message": "Full sync triggered for all destinations",
        }


async def _sync_destination(destination: str) -> None:
    """Background task to sync a specific destination."""
    from src.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await price_sync_service.sync_destination(destination, db)


@router.get("/sync/destinations")
async def get_sync_destinations(
    current_user: User = Depends(get_current_superuser),
) -> dict:
    """Get list of destinations configured for sync."""
    return {
        "destinations": price_sync_service._destinations,
    }


@router.post("/sync/destinations")
async def set_sync_destinations(
    destinations: list[str],
    current_user: User = Depends(get_current_superuser),
) -> dict:
    """Set the list of destinations to sync."""
    price_sync_service.set_destinations(destinations)
    return {
        "status": "updated",
        "destinations": price_sync_service._destinations,
    }
