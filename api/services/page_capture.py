"""
Playwright-based page capture service.
Renders URL, takes screenshots (ATF + Full), and extracts DOM content.
"""
import os
import sys
import time
import datetime
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# Note: Event loop policy should be set in main.py before FastAPI starts
# We can't change it here as the loop is already running

# Get project root (parent of api directory)
_project_root = Path(__file__).parent.parent.parent
_artifact_dir_env = os.getenv("ARTIFACT_DIR")
if _artifact_dir_env:
    ARTIFACT_DIR = os.path.abspath(_artifact_dir_env)
else:
    ARTIFACT_DIR = str(_project_root / "api" / "artifacts")


def _utc_now():
    """Get current UTC timestamp in ISO format."""
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _capture_sync(url: str, atf_path: str, full_path: str, viewport: dict) -> tuple:
    """Synchronous wrapper for Playwright using sync API."""
    from playwright.sync_api import sync_playwright
    
    html = ""
    title = ""
    readable = ""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            # Create context with real Chrome user-agent
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport=viewport
            )
            page = context.new_page()
            
            # Use domcontentloaded with explicit timeout and wait
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )
            page.wait_for_timeout(3000)
            
            # Simple auto-scroll to load lazy sections (reduced iterations for speed)
            for _ in range(3):
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(200)
            
            # Back to top for ATF capture
            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_timeout(150)
            
            # Take screenshots
            page.screenshot(path=atf_path, full_page=False)
            page.screenshot(path=full_path, full_page=True)
            
            # Extract content
            html = page.content()
            title = page.title()
            
            # Readable text (rough): body innerText
            readable = page.evaluate("() => document.body ? document.body.innerText : ''")
            
            page.close()
            context.close()
        except Exception as e:
            logger.exception(f"Error during page capture for {url}: {e}")
            raise
        finally:
            browser.close()
    
    return html, title, readable


async def capture_page_artifacts(url: str) -> Dict[str, Any]:
    """
    Capture page artifacts using Playwright:
    - Screenshots (ATF + Full page)
    - HTML content
    - Readable text
    
    Args:
        url: URL to capture
        
    Returns:
        Dictionary with screenshots paths, DOM content, and metadata
    """
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    
    ts = int(time.time())
    atf_path = os.path.join(ARTIFACT_DIR, f"atf_{ts}.png")
    full_path = os.path.join(ARTIFACT_DIR, f"full_{ts}.png")
    
    viewport = {"width": 1440, "height": 900}
    
    try:
        # Run Playwright in a thread pool to avoid event loop conflicts
        loop = asyncio.get_event_loop()
        html, title, readable = await loop.run_in_executor(
            None,  # Use default executor (ThreadPoolExecutor)
            _capture_sync,
            url, atf_path, full_path, viewport
        )
    except Exception as e:
        # Log exception with full traceback
        logger.exception(f"Playwright error while capturing {url}: {type(e).__name__}: {str(e)}")
        # Re-raise with more context
        error_msg = f"Playwright error while capturing {url}: {type(e).__name__}: {str(e)}"
        print(f"❌ {error_msg}")
        raise Exception(error_msg) from e
    
    # Keep excerpts to avoid huge payloads
    html_excerpt = html[:20000] if html else ""
    readable_excerpt = (readable or "")[:20000]
    
    return {
        "timestamp_utc": _utc_now(),
        "viewport": viewport,
        "screenshots": {
            "above_the_fold": atf_path,
            "full_page": full_path,
            "sections": []
        },
        "dom": {
            "title": title,
            "html_excerpt": html_excerpt,
            "readable_text_excerpt": readable_excerpt
        }
    }

