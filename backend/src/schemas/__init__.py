"""Pydantic schemas for request/response validation."""

from src.schemas.alert import (
    AlertCreate,
    AlertListResponse,
    AlertResponse,
    AlertUpdate,
    AlertWithTourResponse,
)
from src.schemas.price_history import (
    PriceHistoryCreate,
    PriceHistoryListResponse,
    PriceHistoryResponse,
    PriceStatsResponse,
)
from src.schemas.tour import (
    TourCreate,
    TourListResponse,
    TourResponse,
    TourSearchParams,
    TourUpdate,
)
from src.schemas.user import (
    LoginRequest,
    Token,
    TokenPayload,
    UserCreate,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "Token",
    "TokenPayload",
    "LoginRequest",
    # Tour
    "TourCreate",
    "TourUpdate",
    "TourResponse",
    "TourListResponse",
    "TourSearchParams",
    # Price History
    "PriceHistoryCreate",
    "PriceHistoryResponse",
    "PriceHistoryListResponse",
    "PriceStatsResponse",
    # Alert
    "AlertCreate",
    "AlertUpdate",
    "AlertResponse",
    "AlertWithTourResponse",
    "AlertListResponse",
]
