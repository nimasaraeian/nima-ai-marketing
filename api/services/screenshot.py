"""
Screenshot capture service for desktop and mobile viewports.
Unified screenshot generation that saves to shared DEBUG_SHOTS_DIR.
"""
import logging
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def capture_url_png_bytes(url: str, viewport: dict = None) -> bytes:
    """
    Capture screenshot from URL using desktop viewport.
    
    Args:
        url: URL to capture
        viewport: Optional viewport dict (default: desktop 1366x768)
        
    Returns:
        PNG bytes
    """
    if viewport is None:
        viewport = {"width": 1366, "height": 768}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport=viewport,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        png = page.screenshot(full_page=True, type="png")
        context.close()
        browser.close()

    if not png or len(png) < 10_000 or not png.startswith(PNG_MAGIC):
        raise RuntimeError(f"invalid_png bytes={0 if not png else len(png)}")
    return png


def capture_url_png_bytes_mobile(url: str) -> bytes:
    """
    Capture screenshot from URL using mobile viewport.
    
    Args:
        url: URL to capture
        
    Returns:
        PNG bytes
    """
    mobile_viewport = {"width": 390, "height": 844}
    return capture_url_png_bytes(url, viewport=mobile_viewport)


def capture_and_save_screenshot(url: str, kind: str = "desktop", viewport: dict = None) -> tuple[bytes, str]:
    """
    Capture screenshot and save to DEBUG_SHOTS_DIR.
    
    Args:
        url: URL to capture
        kind: "desktop" or "mobile"
        viewport: Optional viewport dict
        
    Returns:
        Tuple of (png_bytes, filename)
    """
    from api.core.config import get_debug_shots_dir
    
    # Capture screenshot
    if kind == "mobile":
        png_bytes = capture_url_png_bytes_mobile(url)
        if viewport is None:
            viewport = {"width": 390, "height": 844}
    else:
        if viewport is None:
            viewport = {"width": 1366, "height": 768}
        png_bytes = capture_url_png_bytes(url, viewport=viewport)
    
    # Save to disk
    debug_dir = get_debug_shots_dir()
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{kind}_{ts}.png"
    file_path = debug_dir / filename
    file_path.write_bytes(png_bytes)
    
    logger.info(f"Screenshot saved: {file_path} ({len(png_bytes)} bytes)")
    
    return png_bytes, filename
