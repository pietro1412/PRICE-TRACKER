"""Tour schemas for request/response validation."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class TourBase(BaseModel):
    """Base tour schema."""

    civitatis_id: int
    name: str
    current_price: Decimal = Field(..., ge=0)
    currency: str = "EUR"
    url: str | None = None
    destination: str | None = None
    destination_id: int | None = None
    category: str | None = None
    rating: Decimal | None = Field(None, ge=0, le=100)


class TourCreate(TourBase):
    """Schema for tour creation."""

    pass


class TourUpdate(BaseModel):
    """Schema for tour update."""

    name: str | None = None
    current_price: Decimal | None = Field(None, ge=0)
    url: str | None = None
    destination: str | None = None
    category: str | None = None
    rating: Decimal | None = Field(None, ge=0, le=100)
    is_active: bool | None = None


class TourResponse(TourBase):
    """Schema for tour response."""

    id: int
    is_active: bool
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    avg_price: Decimal | None = None
    first_seen_at: datetime
    last_scraped_at: datetime

    model_config = {"from_attributes": True}


class TourListResponse(BaseModel):
    """Schema for paginated tour list."""

    items: list[TourResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TourSearchParams(BaseModel):
    """Schema for tour search parameters."""

    destination: str | None = None
    category: str | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    search: str | None = None
    is_active: bool = True
