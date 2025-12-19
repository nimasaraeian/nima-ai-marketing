"""
Centralized configuration module for API.

Handles environment variable loading with safe fallbacks for local development.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file at module import time
# Try project root first, then api directory
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
else:
    # Fallback to api/.env if it exists
    api_env = Path(__file__).parent.parent / ".env"
    if api_env.exists():
        load_dotenv(api_env, override=True)
    else:
        # Last resort: load from current directory
        load_dotenv()


def get_env(name: str, default: str | None = None) -> str | None:
    """
    Get environment variable with safe handling of empty/null values.
    
    Args:
        name: Environment variable name
        default: Default value if not set or empty
        
    Returns:
        Environment variable value or default
    """
    v = os.getenv(name)
    # Treat empty string, "null", "None" as missing
    if v in (None, "", "null", "None"):
        return default
    return v


def is_local_dev() -> bool:
    """
    Determine if running in local development mode.
    
    Checks ENV, APP_ENV, NODE_ENV environment variables.
    Returns True if unset or set to dev/development/local.
    
    Returns:
        True if local development, False otherwise
    """
    env = (
        get_env("ENV") or 
        get_env("APP_ENV") or 
        get_env("NODE_ENV") or 
        ""
    ).lower()
    return env in ("", "dev", "development", "local")


def get_main_brain_backend_url() -> str:
    """
    Get main brain backend URL with safe fallback for local development.
    
    Checks MAIN_BRAIN_BACKEND_URL first, then BRAIN_BACKEND_URL.
    In local dev, falls back to http://127.0.0.1:8000.
    In production, raises RuntimeError if not configured.
    
    Returns:
        Backend URL (without trailing slash)
        
    Raises:
        RuntimeError: If not configured in production
    """
    # Prefer MAIN_BRAIN_BACKEND_URL, then BRAIN_BACKEND_URL
    url = get_env("MAIN_BRAIN_BACKEND_URL") or get_env("BRAIN_BACKEND_URL")
    
    # Check if we're in local dev mode
    local_dev = is_local_dev()
    
    # Local fallback - always use localhost in local dev if URL not set
    if not url and local_dev:
        url = "http://127.0.0.1:8000"
        # Log that we're using fallback
        import logging
        logger = logging.getLogger("config")
        logger.debug(f"Using local fallback backend URL: {url}")
    
    if not url:
        # Production: fail loudly with clear message
        # But first, double-check if we're actually in local dev
        # (in case is_local_dev() returned False incorrectly)
        if is_local_dev():
            # If we're actually in local dev, use fallback instead of failing
            url = "http://127.0.0.1:8000"
            import logging
            logger = logging.getLogger("config")
            logger.warning(f"Backend URL not set, using local fallback: {url}")
        else:
            # Production: fail loudly with clear message
            raise RuntimeError(
                "Main brain backend URL not configured. "
                "Set MAIN_BRAIN_BACKEND_URL or BRAIN_BACKEND_URL environment variable."
            )
    
    return url.rstrip("/")


def get_debug_env_info() -> dict:
    """
    Get environment variable info for debugging (local dev only).
    
    Returns:
        Dict with environment variable values (sanitized)
    """
    return {
        "ENV": get_env("ENV") or "(not set)",
        "APP_ENV": get_env("APP_ENV") or "(not set)",
        "NODE_ENV": get_env("NODE_ENV") or "(not set)",
        "MAIN_BRAIN_BACKEND_URL": get_env("MAIN_BRAIN_BACKEND_URL") or "(not set)",
        "BRAIN_BACKEND_URL": get_env("BRAIN_BACKEND_URL") or "(not set)",
        "is_local_dev": is_local_dev(),
        "computed_backend_url": get_main_brain_backend_url() if is_local_dev() else "(production - not shown)",
    }

