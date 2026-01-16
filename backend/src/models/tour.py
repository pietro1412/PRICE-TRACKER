"""Tour model for tracking Civitatis tours."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Tour(Base):
    """Tour information from Civitatis."""

    __tablename__ = "tours"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    civitatis_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    destination_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")

    # Current price snapshot
    current_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Tracking metadata
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    # Price statistics (computed from history)
    min_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    avg_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Relationships
    price_history: Mapped[list["PriceHistory"]] = relationship(  # noqa: F821
        "PriceHistory", back_populates="tour", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(  # noqa: F821
        "Alert", back_populates="tour", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_tours_destination_category", "destination", "category"),
    )

    def __repr__(self) -> str:
        return f"<Tour(id={self.id}, name={self.name[:50]}, price={self.current_price})>"
