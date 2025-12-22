#!/bin/sh
set -e

echo "Starting API..."
echo "PORT is: ${PORT:-8000}"

# IMPORTANT: make sure this import path matches your app
# Current setting: api.main:app
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}" --timeout-keep-alive 75
