#!/bin/bash
# Start development environment

set -e

echo "Starting Price Tracker (Development)..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Start services
docker-compose up -d

echo ""
echo "Services started successfully!"
echo ""
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/api/docs"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
