"""Alert model for price notifications."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class AlertType(str, Enum):
    """Types of price alerts."""

    PRICE_DROP = "price_drop"  # Alert when price drops below threshold
    PRICE_INCREASE = "price_increase"  # Alert when price increases above threshold
    PRICE_CHANGE = "price_change"  # Alert on any price change
    PERCENTAGE_DROP = "percentage_drop"  # Alert when price drops by percentage


class AlertStatus(str, Enum):
    """Status of an alert."""

    ACTIVE = "active"
    TRIGGERED = "triggered"
    PAUSED = "paused"
    EXPIRED = "expired"


class Alert(Base):
    """Price alert configuration for a tour."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tour_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tours.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Alert configuration
    alert_type: Mapped[AlertType] = mapped_column(String(50), nullable=False)
    threshold_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    threshold_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Alert state
    status: Mapped[AlertStatus] = mapped_column(String(20), default=AlertStatus.ACTIVE)
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trigger_count: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="alerts")  # noqa: F821
    tour: Mapped["Tour"] = relationship("Tour", back_populates="alerts")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, type={self.alert_type}, status={self.status})>"
