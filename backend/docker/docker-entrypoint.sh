#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the main application
echo "Starting MQTT ingestion service..."
exec python main.py
