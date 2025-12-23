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

# Use centralized paths from api.paths
from api.paths import ARTIFACTS_DIR


def _utc_now():
    """Get current UTC timestamp in ISO format."""
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _prepare_page_for_atf(page):
    """
    Helper function to prepare page for ATF screenshot.
    Ensures page is fully rendered and scrolled to top.
    
    Steps:
    1. Wait for DOM content loaded
    2. Wait for network idle (with timeout fallback)
    3. Wait for document ready state
    4. Force scroll to top
    5. Wait for fonts to load
    6. Final delay for render completion
    """
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    
    # Wait for DOM content loaded
    try:
        page.wait_for_load_state("domcontentloaded", timeout=30000)
    except PlaywrightTimeoutError:
        logger.warning("Timeout waiting for domcontentloaded, continuing...")
    
    # Wait for network idle (with timeout - some sites never become idle)
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
        logger.warning("Timeout waiting for networkidle, continuing...")
    
    # Wait for document ready state
    try:
        page.wait_for_function("document.readyState === 'complete'", timeout=10000)
    except PlaywrightTimeoutError:
        logger.warning("Timeout waiting for document.readyState, continuing...")
    
    # Force scroll to top BEFORE ATF screenshot
    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(500)  # Wait for scroll to complete
    
    # Wait for fonts to load (if available)
    try:
        page.evaluate("""
            () => {
                if (document.fonts && document.fonts.ready) {
                    return document.fonts.ready;
                }
                return Promise.resolve();
            }
        """)
        page.wait_for_timeout(200)  # Additional delay after fonts
    except Exception:
        # If fonts API is not available, just wait a bit
        page.wait_for_timeout(200)


def _capture_viewport_sync(
    url: str, 
    atf_path: str, 
    full_path: str, 
    viewport: dict,
    is_mobile: bool = False
) -> tuple:
    """
    Synchronous wrapper for Playwright using sync API.
    Captures ATF and full page screenshots for a specific viewport.
    
    IMPORTANT: ATF screenshot is taken from the TOP of the page (no scrolling before ATF).
    
    Args:
        url: URL to capture
        atf_path: Path to save ATF screenshot
        full_path: Path to save full page screenshot
        viewport: Viewport dict with width and height
        is_mobile: Whether to enable mobile emulation
        
    Returns:
        Tuple of (html, title, readable)
    """
    from playwright.sync_api import sync_playwright
    
    html = ""
    title = ""
    readable = ""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            # Mobile emulation settings
            device_scale_factor = 2 if is_mobile else 1
            has_touch = is_mobile
            is_mobile_device = is_mobile
            
            # Mobile user agent (iPhone Safari)
            mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
            desktop_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            
            # Create context with appropriate settings
            # IMPORTANT: Create a NEW context for mobile (do not reuse desktop page)
            context_options = {
                "viewport": viewport,
                "user_agent": mobile_ua if is_mobile else desktop_ua,
            }
            
            # Add mobile emulation if needed
            if is_mobile:
                context_options.update({
                    "device_scale_factor": device_scale_factor,
                    "has_touch": has_touch,
                    "is_mobile": is_mobile_device,
                })
            
            context = browser.new_context(**context_options)
            page = context.new_page()
            
            # Navigate to URL
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )
            
            # Prepare page for ATF capture (wait for render, scroll to top)
            _prepare_page_for_atf(page)
            
            # Take ATF screenshot FIRST (from top, no scrolling)
            # This ensures we capture the actual "above the fold" content
            page.screenshot(path=atf_path, full_page=False)
            
            # Now scroll down to load lazy sections for full page screenshot
            # Simple auto-scroll to load lazy sections
            for _ in range(3):
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(200)
            
            # Take full page screenshot
            page.screenshot(path=full_path, full_page=True)
            
            # Extract content (use desktop page for content extraction)
            if not is_mobile:
                html = page.content()
                title = page.title()
                # Readable text (rough): body innerText
                readable = page.evaluate("() => document.body ? document.body.innerText : ''")
            
            page.close()
            context.close()
        except Exception as e:
            logger.exception(f"Error during page capture for {url} (mobile={is_mobile}): {e}")
            raise
        finally:
            browser.close()
    
    return html, title, readable


async def capture_page_artifacts(url: str) -> Dict[str, Any]:
    """
    Capture page artifacts using Playwright:
    - Screenshots (Desktop ATF + Full, Mobile ATF + Full)
    - HTML content
    - Readable text
    
    Args:
        url: URL to capture
        
    Returns:
        Dictionary with screenshots paths, DOM content, and metadata
    """
    # Ensure directory exists (already done in api.paths, but ensure anyway)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    
    ts = int(time.time())
    
    # Desktop viewport
    desktop_viewport = {"width": 1365, "height": 768}
    desktop_atf_filename = f"atf_desktop_{ts}.png"
    desktop_full_filename = f"full_desktop_{ts}.png"
    desktop_atf_path = ARTIFACTS_DIR / desktop_atf_filename
    desktop_full_path = ARTIFACTS_DIR / desktop_full_filename
    
    # Mobile viewport
    mobile_viewport = {"width": 390, "height": 844}
    mobile_atf_filename = f"atf_mobile_{ts}.png"
    mobile_full_filename = f"full_mobile_{ts}.png"
    mobile_atf_path = ARTIFACTS_DIR / mobile_atf_filename
    mobile_full_path = ARTIFACTS_DIR / mobile_full_filename
    
    html = ""
    title = ""
    readable = ""
    
    try:
        # Run Playwright in a thread pool to avoid event loop conflicts
        loop = asyncio.get_event_loop()
        
        # Capture desktop screenshots (also extract HTML/title/readable from desktop)
        html, title, readable = await loop.run_in_executor(
            None,  # Use default executor (ThreadPoolExecutor)
            _capture_viewport_sync,
            url, str(desktop_atf_path), str(desktop_full_path), desktop_viewport, False
        )
        
        # Capture mobile screenshots (don't extract content again, use desktop)
        await loop.run_in_executor(
            None,
            _capture_viewport_sync,
            url, str(mobile_atf_path), str(mobile_full_path), mobile_viewport, True
        )
        
        # Verify all screenshots were saved
        screenshots_to_check = [
            (desktop_atf_path, "Desktop ATF"),
            (desktop_full_path, "Desktop Full"),
            (mobile_atf_path, "Mobile ATF"),
            (mobile_full_path, "Mobile Full"),
        ]
        
        for screenshot_path, name in screenshots_to_check:
            if not screenshot_path.exists():
                raise RuntimeError(f"ARTIFACT_MISSING: {name} screenshot not saved: {screenshot_path}")
            if screenshot_path.stat().st_size == 0:
                raise RuntimeError(f"ARTIFACT_INVALID: {name} screenshot is empty: {screenshot_path}")
        
        logger.info(
            f"Screenshots verified: "
            f"Desktop ATF={desktop_atf_path.stat().st_size} bytes, "
            f"Desktop Full={desktop_full_path.stat().st_size} bytes, "
            f"Mobile ATF={mobile_atf_path.stat().st_size} bytes, "
            f"Mobile Full={mobile_full_path.stat().st_size} bytes"
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
    
    # Fix title encoding (UTF-8 decode)
    try:
        if title:
            # Try to fix common encoding issues
            title = title.encode('latin-1', errors='ignore').decode('utf-8', errors='ignore')
    except Exception:
        pass  # Keep original title if encoding fix fails
    
    return {
        "timestamp_utc": _utc_now(),
        "screenshots": {
            "desktop": {
                "above_the_fold": desktop_atf_filename,  # Only filename, not full path
                "full_page": desktop_full_filename,  # Only filename, not full path
                "viewport": desktop_viewport
            },
            "mobile": {
                "above_the_fold": mobile_atf_filename,  # Only filename, not full path
                "full_page": mobile_full_filename,  # Only filename, not full path
                "viewport": mobile_viewport
            }
        },
        "dom": {
            "title": title,
            "html_excerpt": html_excerpt,
            "readable_text_excerpt": readable_excerpt
        }
    }

