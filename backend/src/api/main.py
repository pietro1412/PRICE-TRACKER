from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.utils.logger import get_logger, setup_logging

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    setup_logging(debug=settings.debug)
    logger.info(
        "Starting Price Tracker API",
        version=settings.app_version,
    )
    yield
    logger.info("Shutting down Price Tracker API")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


# Routes will be added here as they are developed
# from src.api.routes import auth, tours, watchlist, alerts, admin
# app.include_router(auth.router, prefix="/api")
# app.include_router(tours.router, prefix="/api")
# app.include_router(watchlist.router, prefix="/api")
# app.include_router(alerts.router, prefix="/api")
# app.include_router(admin.router, prefix="/api")
