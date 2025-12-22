#!/usr/bin/env bash
set -e

# Railway provides PORT; fallback to 8080 (Railway default) or 8000
export PORT="${PORT:-8080}"

# Guarantee LOADER_DIR exists in production
export LOADER_DIR="${LOADER_DIR:-/app/loaders}"

echo "BOOT OK | PORT=$PORT | LOADER_DIR=$LOADER_DIR"

# Ensure app binds to 0.0.0.0 (all interfaces) and uses $PORT
# This is critical for Railway deployment
# Using api.app:app as canonical entrypoint (imports from api.main)
exec uvicorn api.app:app --host 0.0.0.0 --port "$PORT" --timeout-keep-alive 75
