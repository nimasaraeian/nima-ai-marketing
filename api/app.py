"""
FastAPI application entrypoint for Railway deployment.

This is the canonical entrypoint that includes ALL routers and mounts.
The app object is imported from api.main to ensure consistency.

Railway Start Command:
  uvicorn api.app:app --host 0.0.0.0 --port $PORT

This module ensures that:
- All routers are included
- Static file mounts are configured
- Health endpoints are available
- Debug endpoints are available
"""
# Import the complete app from api.main
# This ensures we use the app that has ALL routers included
from api.main import app

# Re-export app for clarity
__all__ = ["app"]

