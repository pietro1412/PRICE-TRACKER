"""API Routes module."""

from src.api.routes.alerts import router as alerts_router
from src.api.routes.auth import router as auth_router
from src.api.routes.price_history import router as price_history_router
from src.api.routes.tours import router as tours_router

__all__ = [
    "auth_router",
    "tours_router",
    "price_history_router",
    "alerts_router",
]
