"""Notification schemas for request/response validation."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """Schema for notification response."""

    id: int
    alert_id: int
    user_id: int
    tour_id: int
    old_price: Decimal
    new_price: Decimal
    price_change: Decimal
    price_change_percent: Decimal
    alert_type: str
    message: str | None
    is_read: bool
    sent_at: datetime

    model_config = {"from_attributes": True}


class NotificationWithTourResponse(NotificationResponse):
    """Schema for notification with tour info."""

    tour_name: str
    tour_destination: str | None


class NotificationListResponse(BaseModel):
    """Schema for paginated notification list."""

    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int
    unread_count: int
