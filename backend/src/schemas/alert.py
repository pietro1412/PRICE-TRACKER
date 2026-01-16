"""Alert schemas for request/response validation."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from src.models.alert import AlertStatus, AlertType


class AlertBase(BaseModel):
    """Base alert schema."""

    tour_id: int
    alert_type: AlertType
    threshold_price: Decimal | None = Field(None, ge=0)
    threshold_percentage: Decimal | None = Field(None, ge=0, le=100)


class AlertCreate(AlertBase):
    """Schema for alert creation."""

    @model_validator(mode="after")
    def validate_threshold(self) -> "AlertCreate":
        """Validate that appropriate threshold is set based on alert type."""
        if self.alert_type == AlertType.PERCENTAGE_DROP:
            if self.threshold_percentage is None:
                raise ValueError("threshold_percentage required for PERCENTAGE_DROP alert")
        else:
            if self.threshold_price is None:
                raise ValueError("threshold_price required for this alert type")
        return self


class AlertUpdate(BaseModel):
    """Schema for alert update."""

    threshold_price: Decimal | None = Field(None, ge=0)
    threshold_percentage: Decimal | None = Field(None, ge=0, le=100)
    status: AlertStatus | None = None


class AlertResponse(AlertBase):
    """Schema for alert response."""

    id: int
    user_id: int
    status: AlertStatus
    last_triggered_at: datetime | None
    trigger_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertWithTourResponse(AlertResponse):
    """Schema for alert response with tour info."""

    tour_name: str
    tour_current_price: Decimal
    tour_destination: str | None


class AlertListResponse(BaseModel):
    """Schema for paginated alert list."""

    items: list[AlertResponse]
    total: int
    page: int
    page_size: int
