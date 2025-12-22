#!/usr/bin/env bash
set -e

# Railway provides PORT; fallback to 8000
export PORT="${PORT:-8000}"

# Guarantee LOADER_DIR exists in production
export LOADER_DIR="${LOADER_DIR:-/app/loaders}"

echo "BOOT OK | PORT=$PORT | LOADER_DIR=$LOADER_DIR"

exec uvicorn api.main:app --host 0.0.0.0 --port "$PORT" --timeout-keep-alive 75
