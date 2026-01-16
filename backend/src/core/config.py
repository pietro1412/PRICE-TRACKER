from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Price Tracker API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/pricetracker"

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174"]

    # Scraping
    scrape_rate_limit_seconds: int = 30
    scrape_max_retries: int = 3

    # Scheduler
    sync_prices_interval_hours: int = 6
    sync_tours_interval_hours: int = 24
    cleanup_days_to_keep: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()
