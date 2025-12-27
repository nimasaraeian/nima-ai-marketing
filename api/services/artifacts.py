"""
Artifact management service - single source of truth for file artifacts.

Handles saving, serving, and URL generation for screenshots and other artifacts.
"""
import os
import base64
import logging
from pathlib import Path
from typing import Optional
from api.core.config import get_artifacts_dir, get_public_base_url, get_env

logger = logging.getLogger(__name__)


def ensure_artifacts_dir() -> Path:
    """
    Ensure artifacts directory exists and return its path.
    
    Returns:
        Path to artifacts directory (always exists after this call)
    """
    artifacts_dir = get_artifacts_dir()
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Artifacts directory ensured: {artifacts_dir}")
    return artifacts_dir


def save_artifact_bytes(filename: str, data: bytes, base_url: Optional[str] = None) -> str:
    """
    Save artifact bytes to disk and return public URL.
    
    Args:
        filename: Filename to save (e.g., "atf_desktop_1234567890.png")
        data: Bytes to save
        base_url: Base URL for public URL (if None, uses get_public_base_url or request)
        
    Returns:
        Absolute public URL to the artifact (e.g., "https://domain.com/api/artifacts/atf_desktop_1234567890.png")
    """
    artifacts_dir = ensure_artifacts_dir()
    file_path = artifacts_dir / filename
    
    try:
        # Save file
        file_path.write_bytes(data)
        logger.info(f"Saved artifact: {filename}, size: {len(data)} bytes, path: {file_path}")
        
        # Generate public URL
        if base_url:
            public_url = f"{base_url.rstrip('/')}/api/artifacts/{filename}"
        else:
            # Try to get from env
            public_base_url = get_public_base_url()
            if public_base_url:
                public_url = f"{public_base_url.rstrip('/')}/api/artifacts/{filename}"
            else:
                # Fallback: relative URL (will be made absolute by frontend or request context)
                public_url = f"/api/artifacts/{filename}"
        
        return public_url
    except Exception as e:
        logger.error(f"Failed to save artifact {filename}: {type(e).__name__}: {e}", exc_info=True)
        raise


def artifact_public_url(filename: str, base_url: Optional[str] = None) -> str:
    """
    Generate public URL for an artifact (without saving).
    
    Args:
        filename: Artifact filename
        base_url: Base URL (if None, uses get_public_base_url)
        
    Returns:
        Absolute public URL
    """
    if base_url:
        return f"{base_url.rstrip('/')}/api/artifacts/{filename}"
    
    public_base_url = get_public_base_url()
    if public_base_url:
        return f"{public_base_url.rstrip('/')}/api/artifacts/{filename}"
    
    # Fallback: relative URL
    return f"/api/artifacts/{filename}"


def file_to_data_uri(file_path: Path, mime: str = "image/png") -> str:
    """
    Read file and convert to base64 data URI.
    
    Args:
        file_path: Path to file
        mime: MIME type (default: "image/png")
        
    Returns:
        Data URI string (e.g., "data:image/png;base64,...")
    """
    try:
        data = file_path.read_bytes()
        b64 = base64.b64encode(data).decode("utf-8")
        return f"data:{mime};base64,{b64}"
    except Exception as e:
        logger.error(f"Failed to read file for data URI: {file_path}: {type(e).__name__}: {e}")
        raise


def bytes_to_data_uri(data: bytes, mime: str = "image/png") -> str:
    """
    Convert bytes to base64 data URI.
    
    Args:
        data: Bytes to convert
        mime: MIME type (default: "image/png")
        
    Returns:
        Data URI string
    """
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"

