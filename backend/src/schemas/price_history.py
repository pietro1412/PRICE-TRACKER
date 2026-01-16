"""Price history schemas for request/response validation."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PriceHistoryBase(BaseModel):
    """Base price history schema."""

    tour_id: int
    price: Decimal
    currency: str = "EUR"


class PriceHistoryCreate(PriceHistoryBase):
    """Schema for price history creation."""

    price_change: Decimal | None = None
    price_change_percent: Decimal | None = None


class PriceHistoryResponse(PriceHistoryBase):
    """Schema for price history response."""

    id: int
    price_change: Decimal | None = None
    price_change_percent: Decimal | None = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class PriceHistoryListResponse(BaseModel):
    """Schema for paginated price history list."""

    items: list[PriceHistoryResponse]
    total: int
    page: int
    page_size: int


class PriceStatsResponse(BaseModel):
    """Schema for price statistics."""

    tour_id: int
    current_price: Decimal
    min_price: Decimal | None
    max_price: Decimal | None
    avg_price: Decimal | None
    price_change_24h: Decimal | None
    price_change_7d: Decimal | None
    price_change_30d: Decimal | None
    total_records: int
