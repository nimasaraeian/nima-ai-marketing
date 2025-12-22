#!/bin/bash
# Startup script for the application
# Handles PORT environment variable and ensures proper startup

set -e  # Exit on error

# Get port from environment variable or default to 8000
PORT=${PORT:-8000}

echo "Starting NIMA AI Marketing API..."
echo "Port: $PORT"
echo "Host: 0.0.0.0"

# Start uvicorn with proper configuration
exec uvicorn api.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --timeout-keep-alive 75 \
    --log-level info

