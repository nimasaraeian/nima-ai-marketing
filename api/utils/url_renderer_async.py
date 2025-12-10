"""
URL Renderer using Playwright Async API

Fully renders JavaScript-heavy pages using a headless browser.
This is essential for modern SPAs and dynamic content.

IMPORTANT: This module uses ONLY async Playwright API to avoid
"using Playwright Sync API inside the asyncio loop" errors.
"""

import logging
from typing import Optional

logger = logging.getLogger("url_renderer_async")

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install")


async def render_url_with_js(url: str, timeout: int = 60000, wait_until: str = "networkidle") -> str:
    """
    Fully renders a URL using a headless browser and returns visible HTML.
    
    This function uses Playwright Async API to:
    - Execute JavaScript
    - Wait for dynamic content to load
    - Return fully rendered HTML
    
    Args:
        url: URL to render
        timeout: Maximum time to wait for page load (milliseconds, default: 60000 = 60 seconds)
        wait_until: When to consider navigation finished:
            - "networkidle": wait until network is idle (no requests for 500ms) - most strict
            - "load": wait for load event - less strict, fallback if networkidle fails
            - "domcontentloaded": wait for DOMContentLoaded event - least strict, last resort
            - "commit": wait for navigation commit
        
    Returns:
        Fully rendered HTML as string
        
    Raises:
        ImportError: If Playwright is not installed
        ValueError: If URL is invalid or page cannot be rendered
        TimeoutError: If page load exceeds timeout
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise ImportError(
            "Playwright is not installed. "
            "Please run: pip install playwright && playwright install chromium"
        )
    
    if not url or not url.strip():
        raise ValueError("URL cannot be empty")
    
    # Ensure URL has scheme
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        async with async_playwright() as p:
            # Launch headless browser
            browser = await p.chromium.launch(headless=True)
            
            try:
                # Create new page
                page = await browser.new_page()
                
                # Set realistic viewport
                await page.set_viewport_size({"width": 1920, "height": 1080})
                
                # Navigate to URL and wait for content to load
                logger.info(f"[URL Renderer Async] Rendering URL: {url} (timeout={timeout}ms, wait_until={wait_until})")
                
                try:
                    # Try with the specified wait condition
                    await page.goto(url, timeout=timeout, wait_until=wait_until)
                except PlaywrightTimeoutError:
                    # If networkidle times out, try with "load" which is less strict
                    if wait_until == "networkidle":
                        logger.warning(f"[URL Renderer Async] networkidle timeout, retrying with 'load' condition")
                        try:
                            await page.goto(url, timeout=timeout, wait_until="load")
                            # Give it a bit more time for JavaScript to execute
                            await page.wait_for_timeout(2000)  # Wait 2 seconds for JS to render
                        except PlaywrightTimeoutError:
                            # Last resort: try domcontentloaded
                            logger.warning(f"[URL Renderer Async] load timeout, trying 'domcontentloaded'")
                            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                            await page.wait_for_timeout(3000)  # Wait 3 seconds for JS to render
                    else:
                        raise
                
                # Get fully rendered HTML
                html = await page.content()
                
                logger.info(f"[URL Renderer Async] Successfully rendered {len(html)} characters from {url}")
                return html
                
            finally:
                # Always close browser
                await browser.close()
            
    except PlaywrightTimeoutError as e:
        timeout_seconds = timeout / 1000
        error_msg = f"Page load timeout after {timeout_seconds}s ({timeout}ms): {e}"
        logger.error(f"[URL Renderer Async] {error_msg}")
        raise ValueError(
            f"Page load timeout after {timeout_seconds} seconds. The website took too long to load.\n\n"
            "This can happen if:\n"
            "- The website is very slow or has heavy JavaScript\n"
            "- The website blocks automated browsers\n"
            "- Network connection is slow\n\n"
            "SOLUTION: Please manually copy and paste the page content:\n"
            "- Hero headline\n"
            "- CTA button text\n"
            "- Price (if visible)\n"
            "- Guarantee/refund information\n\n"
            "Then paste this content directly in the input field instead of using the URL."
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[URL Renderer Async] Error rendering URL {url}: {error_msg}")
        
        # Check for common error patterns
        if "net::ERR" in error_msg or "Navigation failed" in error_msg:
            raise ValueError(
                f"Failed to access URL: {error_msg}\n\n"
                "SOLUTION: Please manually copy and paste the page content:\n"
                "- Hero headline\n"
                "- CTA button text\n"
                "- Price (if visible)\n"
                "- Guarantee/refund information\n\n"
                "Then paste this content directly in the input field instead of using the URL."
            )
        
        raise ValueError(
            f"Failed to render URL: {error_msg}\n\n"
            "SOLUTION: Please manually copy and paste the page content:\n"
            "- Hero headline\n"
            "- CTA button text\n"
            "- Price (if visible)\n"
            "- Guarantee/refund information\n\n"
            "Then paste this content directly in the input field instead of using the URL."
        )

