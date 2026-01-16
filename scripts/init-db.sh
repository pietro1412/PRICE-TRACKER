#!/bin/bash
# Initialize database with migrations

set -e

echo "Initializing database..."

# Run migrations
docker-compose exec backend alembic upgrade head

echo "Database initialized successfully!"
