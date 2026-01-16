"""Price synchronization service.

Handles syncing tour prices from Civitatis and updating the database.
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.database import AsyncSessionLocal
from src.models import PriceHistory, Tour
from src.services.civitatis_scraper import TourData, civitatis_scraper
from src.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class PriceSyncService:
    """Service for synchronizing tour prices from Civitatis."""

    # Default destinations to scrape
    DEFAULT_DESTINATIONS = [
        "rome",
        "florence",
        "venice",
        "milan",
        "naples",
        "paris",
        "barcelona",
        "madrid",
        "london",
        "amsterdam",
    ]

    def __init__(self):
        self._destinations = self.DEFAULT_DESTINATIONS.copy()

    def set_destinations(self, destinations: list[str]) -> None:
        """Set the list of destinations to scrape."""
        self._destinations = destinations

    async def sync_destination(
        self,
        destination: str,
        db: AsyncSession,
    ) -> dict:
        """
        Sync all tours for a specific destination.

        Returns:
            Dict with sync statistics
        """
        stats = {
            "destination": destination,
            "tours_found": 0,
            "tours_created": 0,
            "tours_updated": 0,
            "price_changes": 0,
            "errors": 0,
        }

        try:
            logger.info(f"Syncing destination: {destination}")
            tours = await civitatis_scraper.get_destination_tours(destination)
            stats["tours_found"] = len(tours)

            for tour_data in tours:
                try:
                    result = await self._sync_tour(tour_data, db)
                    if result == "created":
                        stats["tours_created"] += 1
                    elif result == "updated":
                        stats["tours_updated"] += 1
                    elif result == "price_changed":
                        stats["tours_updated"] += 1
                        stats["price_changes"] += 1
                except Exception as e:
                    logger.error(f"Error syncing tour {tour_data.civitatis_id}: {e}")
                    stats["errors"] += 1

            await db.commit()
            logger.info(
                f"Destination {destination} synced",
                tours_found=stats["tours_found"],
                created=stats["tours_created"],
                updated=stats["tours_updated"],
                price_changes=stats["price_changes"],
            )

        except Exception as e:
            logger.error(f"Error syncing destination {destination}: {e}")
            stats["errors"] += 1
            await db.rollback()

        return stats

    async def _sync_tour(
        self,
        tour_data: TourData,
        db: AsyncSession,
    ) -> str:
        """
        Sync a single tour to the database.

        Returns:
            'created', 'updated', or 'price_changed'
        """
        # Check if tour exists
        result = await db.execute(
            select(Tour).where(Tour.civitatis_id == tour_data.civitatis_id)
        )
        existing_tour = result.scalar_one_or_none()

        if existing_tour is None:
            # Create new tour
            tour = Tour(
                civitatis_id=tour_data.civitatis_id,
                name=tour_data.name,
                current_price=tour_data.price,
                currency=tour_data.currency,
                url=tour_data.url,
                destination=tour_data.destination,
                destination_id=tour_data.destination_id,
                category=tour_data.category,
                rating=tour_data.rating,
                min_price=tour_data.price,
                max_price=tour_data.price,
                avg_price=tour_data.price,
            )
            db.add(tour)
            await db.flush()

            # Add initial price history
            price_record = PriceHistory(
                tour_id=tour.id,
                price=tour_data.price,
                currency=tour_data.currency,
            )
            db.add(price_record)

            return "created"

        # Update existing tour
        old_price = existing_tour.current_price
        price_changed = old_price != tour_data.price

        existing_tour.name = tour_data.name
        existing_tour.current_price = tour_data.price
        existing_tour.url = tour_data.url or existing_tour.url
        existing_tour.category = tour_data.category or existing_tour.category
        existing_tour.rating = tour_data.rating or existing_tour.rating
        existing_tour.last_scraped_at = datetime.now(timezone.utc)
        existing_tour.is_active = True

        if price_changed:
            # Calculate price change
            price_change = tour_data.price - old_price
            price_change_percent = (
                (price_change / old_price * 100) if old_price > 0 else Decimal(0)
            )

            # Add price history record
            price_record = PriceHistory(
                tour_id=existing_tour.id,
                price=tour_data.price,
                currency=tour_data.currency,
                price_change=price_change,
                price_change_percent=price_change_percent,
            )
            db.add(price_record)

            # Update price statistics
            await self._update_price_stats(existing_tour.id, db)

            logger.info(
                f"Price changed for tour {existing_tour.id}",
                tour_name=existing_tour.name[:50],
                old_price=float(old_price),
                new_price=float(tour_data.price),
                change=float(price_change),
                change_percent=float(price_change_percent),
            )

            return "price_changed"

        return "updated"

    async def _update_price_stats(
        self,
        tour_id: int,
        db: AsyncSession,
    ) -> None:
        """Update min/max/avg price statistics for a tour."""
        stats_query = select(
            func.min(PriceHistory.price).label("min_price"),
            func.max(PriceHistory.price).label("max_price"),
            func.avg(PriceHistory.price).label("avg_price"),
        ).where(PriceHistory.tour_id == tour_id)

        result = await db.execute(stats_query)
        stats = result.one()

        await db.execute(
            update(Tour)
            .where(Tour.id == tour_id)
            .values(
                min_price=stats.min_price,
                max_price=stats.max_price,
                avg_price=stats.avg_price,
            )
        )

    async def sync_all_destinations(self) -> dict:
        """
        Sync all configured destinations.

        Returns:
            Dict with overall sync statistics
        """
        overall_stats = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "destinations_synced": 0,
            "total_tours_found": 0,
            "total_tours_created": 0,
            "total_tours_updated": 0,
            "total_price_changes": 0,
            "total_errors": 0,
            "destination_stats": [],
        }

        logger.info(
            "Starting full price sync",
            destinations=len(self._destinations),
        )

        async with AsyncSessionLocal() as db:
            for destination in self._destinations:
                stats = await self.sync_destination(destination, db)
                overall_stats["destination_stats"].append(stats)
                overall_stats["destinations_synced"] += 1
                overall_stats["total_tours_found"] += stats["tours_found"]
                overall_stats["total_tours_created"] += stats["tours_created"]
                overall_stats["total_tours_updated"] += stats["tours_updated"]
                overall_stats["total_price_changes"] += stats["price_changes"]
                overall_stats["total_errors"] += stats["errors"]

        overall_stats["finished_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Full price sync completed",
            destinations=overall_stats["destinations_synced"],
            tours_found=overall_stats["total_tours_found"],
            created=overall_stats["total_tours_created"],
            updated=overall_stats["total_tours_updated"],
            price_changes=overall_stats["total_price_changes"],
            errors=overall_stats["total_errors"],
        )

        return overall_stats

    async def sync_active_tours(self) -> dict:
        """
        Sync prices for all active tours in the database.

        This is more efficient when you have a known set of tours
        and want to update only their prices.

        Returns:
            Dict with sync statistics
        """
        stats = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "tours_checked": 0,
            "tours_updated": 0,
            "price_changes": 0,
            "errors": 0,
        }

        logger.info("Starting active tours price sync")

        async with AsyncSessionLocal() as db:
            # Get all active tours grouped by destination
            result = await db.execute(
                select(Tour.destination)
                .where(Tour.is_active == True)  # noqa: E712
                .where(Tour.destination.isnot(None))
                .distinct()
            )
            destinations = [r[0] for r in result.all()]

            for destination in destinations:
                try:
                    dest_stats = await self.sync_destination(destination.lower(), db)
                    stats["tours_checked"] += dest_stats["tours_found"]
                    stats["tours_updated"] += dest_stats["tours_updated"]
                    stats["price_changes"] += dest_stats["price_changes"]
                    stats["errors"] += dest_stats["errors"]
                except Exception as e:
                    logger.error(f"Error syncing destination {destination}: {e}")
                    stats["errors"] += 1

        stats["finished_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Active tours price sync completed",
            tours_checked=stats["tours_checked"],
            updated=stats["tours_updated"],
            price_changes=stats["price_changes"],
            errors=stats["errors"],
        )

        return stats


# Global service instance
price_sync_service = PriceSyncService()
