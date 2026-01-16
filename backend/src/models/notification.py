"""Notification model for storing alert notification history."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Notification(Base):
    """Record of a triggered alert notification."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    alert_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tour_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tours.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Price information at time of trigger
    old_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    new_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_change: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_change_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    # Alert details
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    is_read: Mapped[bool] = mapped_column(default=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    alert: Mapped["Alert"] = relationship("Alert")  # noqa: F821
    user: Mapped["User"] = relationship("User")  # noqa: F821
    tour: Mapped["Tour"] = relationship("Tour")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, alert_id={self.alert_id}, user_id={self.user_id})>"
