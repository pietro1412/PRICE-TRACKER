# Price Tracker Backend

FastAPI backend for the tour price tracking system.

## Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy (async)
- PostgreSQL
- Alembic
- Playwright (scraping)

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start server
uvicorn src.api.main:app --reload
```

## API Documentation

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
