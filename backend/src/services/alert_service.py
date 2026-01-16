"""Alert service for checking and triggering price alerts.

Monitors price changes and triggers alerts based on user configurations.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.database import AsyncSessionLocal
from src.models import Alert, AlertStatus, AlertType, Notification, Tour, User
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AlertNotification:
    """Represents a triggered alert notification."""

    alert_id: int
    user_id: int
    user_email: str
    tour_id: int
    tour_name: str
    alert_type: AlertType
    old_price: Decimal
    new_price: Decimal
    price_change: Decimal
    price_change_percent: Decimal
    threshold_price: Decimal | None
    threshold_percentage: Decimal | None
    triggered_at: datetime

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "tour_id": self.tour_id,
            "tour_name": self.tour_name,
            "alert_type": self.alert_type.value,
            "old_price": float(self.old_price),
            "new_price": float(self.new_price),
            "price_change": float(self.price_change),
            "price_change_percent": float(self.price_change_percent),
            "threshold_price": float(self.threshold_price) if self.threshold_price else None,
            "threshold_percentage": float(self.threshold_percentage) if self.threshold_percentage else None,
            "triggered_at": self.triggered_at.isoformat(),
        }


class AlertService:
    """Service for managing and triggering price alerts."""

    def __init__(self):
        self._notification_handlers: list = []

    def add_notification_handler(self, handler) -> None:
        """Add a handler to be called when alerts are triggered."""
        self._notification_handlers.append(handler)

    async def check_alerts_for_tour(
        self,
        tour_id: int,
        old_price: Decimal,
        new_price: Decimal,
        db: AsyncSession,
    ) -> list[AlertNotification]:
        """
        Check all active alerts for a tour after a price change.

        Args:
            tour_id: The tour ID
            old_price: Previous price
            new_price: New price
            db: Database session

        Returns:
            List of triggered alert notifications
        """
        if old_price == new_price:
            return []

        price_change = new_price - old_price
        price_change_percent = (
            (price_change / old_price * 100) if old_price > 0 else Decimal(0)
        )

        # Get tour info
        tour_result = await db.execute(select(Tour).where(Tour.id == tour_id))
        tour = tour_result.scalar_one_or_none()
        if not tour:
            return []

        # Get all active alerts for this tour with user info
        alerts_query = (
            select(Alert)
            .options(selectinload(Alert.user))
            .where(Alert.tour_id == tour_id)
            .where(Alert.status == AlertStatus.ACTIVE)
        )
        result = await db.execute(alerts_query)
        alerts = result.scalars().all()

        triggered_notifications = []

        for alert in alerts:
            should_trigger = self._should_trigger_alert(
                alert=alert,
                old_price=old_price,
                new_price=new_price,
                price_change=price_change,
                price_change_percent=price_change_percent,
            )

            if should_trigger:
                notification = AlertNotification(
                    alert_id=alert.id,
                    user_id=alert.user_id,
                    user_email=alert.user.email,
                    tour_id=tour_id,
                    tour_name=tour.name,
                    alert_type=alert.alert_type,
                    old_price=old_price,
                    new_price=new_price,
                    price_change=price_change,
                    price_change_percent=price_change_percent,
                    threshold_price=alert.threshold_price,
                    threshold_percentage=alert.threshold_percentage,
                    triggered_at=datetime.now(timezone.utc),
                )
                triggered_notifications.append(notification)

                # Update alert status
                await self._mark_alert_triggered(alert.id, db)

                logger.info(
                    "Alert triggered",
                    alert_id=alert.id,
                    user_email=alert.user.email,
                    tour_name=tour.name[:50],
                    alert_type=alert.alert_type.value,
                    old_price=float(old_price),
                    new_price=float(new_price),
                )

        # Send notifications
        if triggered_notifications:
            await self._send_notifications(triggered_notifications)

        return triggered_notifications

    def _should_trigger_alert(
        self,
        alert: Alert,
        old_price: Decimal,
        new_price: Decimal,
        price_change: Decimal,
        price_change_percent: Decimal,
    ) -> bool:
        """Determine if an alert should be triggered based on its type."""

        if alert.alert_type == AlertType.PRICE_DROP:
            # Trigger when price drops below threshold
            return (
                new_price < old_price
                and alert.threshold_price is not None
                and new_price <= alert.threshold_price
            )

        elif alert.alert_type == AlertType.PRICE_INCREASE:
            # Trigger when price increases above threshold
            return (
                new_price > old_price
                and alert.threshold_price is not None
                and new_price >= alert.threshold_price
            )

        elif alert.alert_type == AlertType.PRICE_CHANGE:
            # Trigger on any price change
            return new_price != old_price

        elif alert.alert_type == AlertType.PERCENTAGE_DROP:
            # Trigger when price drops by specified percentage
            return (
                price_change < 0
                and alert.threshold_percentage is not None
                and abs(price_change_percent) >= alert.threshold_percentage
            )

        return False

    async def _mark_alert_triggered(
        self,
        alert_id: int,
        db: AsyncSession,
    ) -> None:
        """Update alert status after being triggered."""
        await db.execute(
            update(Alert)
            .where(Alert.id == alert_id)
            .values(
                last_triggered_at=datetime.now(timezone.utc),
                trigger_count=Alert.trigger_count + 1,
            )
        )

    async def _send_notifications(
        self,
        notifications: list[AlertNotification],
    ) -> None:
        """Send notifications through registered handlers."""
        for handler in self._notification_handlers:
            try:
                await handler(notifications)
            except Exception as e:
                logger.error(f"Notification handler error: {e}")

        # Always log notifications
        for notification in notifications:
            await self._log_notification(notification)

    async def _log_notification(self, notification: AlertNotification) -> None:
        """Log a notification and save to database."""
        logger.info(
            "Alert notification",
            alert_id=notification.alert_id,
            user_email=notification.user_email,
            tour_name=notification.tour_name[:50],
            alert_type=notification.alert_type.value,
            price_change=float(notification.price_change),
            price_change_percent=float(notification.price_change_percent),
        )

        # Save notification to database
        async with AsyncSessionLocal() as db:
            db_notification = Notification(
                alert_id=notification.alert_id,
                user_id=notification.user_id,
                tour_id=notification.tour_id,
                old_price=notification.old_price,
                new_price=notification.new_price,
                price_change=notification.price_change,
                price_change_percent=notification.price_change_percent,
                alert_type=notification.alert_type.value,
                message=(
                    f"Il prezzo del tour '{notification.tour_name}' è cambiato da "
                    f"€{notification.old_price:.2f} a €{notification.new_price:.2f}"
                ),
            )
            db.add(db_notification)
            await db.commit()

    async def check_all_pending_alerts(self) -> dict:
        """
        Check all active alerts against current tour prices.
        Useful for catching up after system downtime.

        Returns:
            Dict with check statistics
        """
        stats = {
            "alerts_checked": 0,
            "alerts_triggered": 0,
            "errors": 0,
        }

        async with AsyncSessionLocal() as db:
            # Get all active alerts with tour info
            alerts_query = (
                select(Alert)
                .options(selectinload(Alert.user), selectinload(Alert.tour))
                .where(Alert.status == AlertStatus.ACTIVE)
            )
            result = await db.execute(alerts_query)
            alerts = result.scalars().all()

            for alert in alerts:
                stats["alerts_checked"] += 1
                try:
                    # For PRICE_DROP alerts, check if current price is below threshold
                    if (
                        alert.alert_type == AlertType.PRICE_DROP
                        and alert.threshold_price is not None
                        and alert.tour.current_price <= alert.threshold_price
                    ):
                        notification = AlertNotification(
                            alert_id=alert.id,
                            user_id=alert.user_id,
                            user_email=alert.user.email,
                            tour_id=alert.tour_id,
                            tour_name=alert.tour.name,
                            alert_type=alert.alert_type,
                            old_price=alert.threshold_price,
                            new_price=alert.tour.current_price,
                            price_change=alert.tour.current_price - alert.threshold_price,
                            price_change_percent=Decimal(0),
                            threshold_price=alert.threshold_price,
                            threshold_percentage=alert.threshold_percentage,
                            triggered_at=datetime.now(timezone.utc),
                        )
                        await self._mark_alert_triggered(alert.id, db)
                        await self._send_notifications([notification])
                        stats["alerts_triggered"] += 1

                except Exception as e:
                    logger.error(f"Error checking alert {alert.id}: {e}")
                    stats["errors"] += 1

            await db.commit()

        logger.info(
            "Pending alerts check completed",
            checked=stats["alerts_checked"],
            triggered=stats["alerts_triggered"],
            errors=stats["errors"],
        )

        return stats


# Global service instance
alert_service = AlertService()


# Email notification handler (placeholder - can be implemented with actual email service)
async def email_notification_handler(notifications: list[AlertNotification]) -> None:
    """
    Handle alert notifications via email.

    This is a placeholder that logs email content.
    Replace with actual email sending logic (e.g., using SendGrid, AWS SES, etc.)
    """
    for notification in notifications:
        email_content = {
            "to": notification.user_email,
            "subject": f"Price Alert: {notification.tour_name[:50]}",
            "body": (
                f"Il prezzo del tour '{notification.tour_name}' è cambiato!\n\n"
                f"Prezzo precedente: €{notification.old_price:.2f}\n"
                f"Nuovo prezzo: €{notification.new_price:.2f}\n"
                f"Variazione: €{notification.price_change:.2f} "
                f"({notification.price_change_percent:.1f}%)\n\n"
                f"Tipo alert: {notification.alert_type.value}\n"
            ),
        }
        logger.info(
            "Email notification queued",
            to=email_content["to"],
            subject=email_content["subject"],
        )


# Register the email handler
alert_service.add_notification_handler(email_notification_handler)
