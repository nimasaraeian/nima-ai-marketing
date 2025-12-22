"""
Screenshot service using Playwright to capture URL screenshots as PNG bytes.
"""
from playwright.sync_api import sync_playwright

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def capture_url_png_bytes(url: str) -> bytes:
    """
    Capture a screenshot of a URL and return PNG bytes.
    
    Args:
        url: The URL to screenshot
        
    Returns:
        PNG image bytes
        
    Raises:
        RuntimeError: If screenshot is invalid (too small, wrong format, etc.)
        ImportError: If Playwright is not installed
        TimeoutError: If page load times out
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
        page = context.new_page()
        r = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        png = page.screenshot(full_page=True, type="png")
        final_url = page.url
        title = page.title()
        context.close()
        browser.close()

    if not isinstance(png, (bytes, bytearray)) or len(png) < 10_000 or not png.startswith(PNG_MAGIC):
        raise RuntimeError(f"screenshot_invalid_png bytes={len(png) if png else 0} final_url={final_url} title={title}")
    return bytes(png)














