"""Price history model for tracking tour price changes over time."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class PriceHistory(Base):
    """Historical price record for a tour."""

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tour_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tours.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(default="EUR")
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Price change from previous record
    price_change: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_change_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Relationship
    tour: Mapped["Tour"] = relationship("Tour", back_populates="price_history")  # noqa: F821

    __table_args__ = (
        Index("ix_price_history_tour_recorded", "tour_id", "recorded_at"),
    )

    def __repr__(self) -> str:
        return f"<PriceHistory(tour_id={self.tour_id}, price={self.price}, recorded_at={self.recorded_at})>"
