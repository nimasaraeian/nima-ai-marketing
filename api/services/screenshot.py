"""
Screenshot service using Playwright to capture URL screenshots as PNG bytes.
"""
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

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
    logger.info(f"Starting screenshot capture for URL: {url}")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox"
                ]
            )
            context = browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Try to load the page with better wait strategy
            try:
                logger.debug(f"Navigating to {url}...")
                response = page.goto(
                    url, 
                    wait_until="load",  # Wait for 'load' event (better than domcontentloaded)
                    timeout=60000  # Increased timeout to 60 seconds
                )
                
                if response and response.status >= 400:
                    logger.warning(f"Page returned status {response.status} for {url}")
                
                # Wait a bit more for dynamic content
                logger.debug("Waiting for page to stabilize...")
                page.wait_for_timeout(2000)  # Increased wait time
                
                # Try to wait for network to be idle (with timeout)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                    logger.debug("Network idle state reached")
                except PlaywrightTimeoutError:
                    logger.warning("Network idle timeout, proceeding with screenshot anyway")
                
            except PlaywrightTimeoutError as e:
                logger.error(f"Page load timeout for {url}: {e}")
                raise TimeoutError(f"Page load timeout after 60 seconds: {url}") from e
            except Exception as e:
                logger.error(f"Error navigating to {url}: {type(e).__name__}: {e}")
                raise RuntimeError(f"Failed to navigate to {url}: {e}") from e
            
            # Capture screenshot
            try:
                logger.debug("Capturing screenshot...")
                png = page.screenshot(full_page=True, type="png")
                final_url = page.url
                title = page.title()
                logger.info(f"Screenshot captured: {len(png)} bytes, final_url={final_url}, title={title[:50]}")
            except Exception as e:
                logger.error(f"Error capturing screenshot: {type(e).__name__}: {e}")
                raise RuntimeError(f"Failed to capture screenshot: {e}") from e
            finally:
                context.close()
                browser.close()

        # Validate screenshot
        if not isinstance(png, (bytes, bytearray)):
            raise RuntimeError(f"screenshot_invalid_type type={type(png)}")
        
        if len(png) < 10_000:
            raise RuntimeError(f"screenshot_too_small bytes={len(png)} final_url={final_url} title={title}")
        
        if not png.startswith(PNG_MAGIC):
            raise RuntimeError(f"screenshot_invalid_format bytes={len(png)} final_url={final_url} title={title}")
        
        logger.info(f"Screenshot validation passed: {len(png)} bytes")
        return bytes(png)
        
    except ImportError as e:
        logger.error(f"Playwright not installed: {e}")
        raise ImportError("Playwright is not installed. Run: pip install playwright && playwright install chromium") from e
    except Exception as e:
        logger.exception(f"Unexpected error in screenshot capture: {type(e).__name__}: {e}")
        raise


def capture_url_png_bytes_mobile(url: str) -> bytes:
    """
    Capture a mobile screenshot of a URL and return PNG bytes.
    
    Args:
        url: The URL to screenshot
        
    Returns:
        PNG image bytes
        
    Raises:
        RuntimeError: If screenshot is invalid (too small, wrong format, etc.)
        ImportError: If Playwright is not installed
        TimeoutError: If page load times out
    """
    logger.info(f"Starting mobile screenshot capture for URL: {url}")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox"
                ]
            )
            # Mobile viewport (iPhone 12 Pro size)
            context = browser.new_context(
                viewport={"width": 390, "height": 844},
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                device_scale_factor=3,
                is_mobile=True,
                has_touch=True
            )
            page = context.new_page()
            
            # Try to load the page with better wait strategy
            try:
                logger.debug(f"Navigating to {url} (mobile)...")
                response = page.goto(
                    url, 
                    wait_until="load",
                    timeout=60000
                )
                
                if response and response.status >= 400:
                    logger.warning(f"Page returned status {response.status} for {url}")
                
                # Wait a bit more for dynamic content
                logger.debug("Waiting for page to stabilize (mobile)...")
                page.wait_for_timeout(2000)
                
                # Try to wait for network to be idle (with timeout)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                    logger.debug("Network idle state reached (mobile)")
                except PlaywrightTimeoutError:
                    logger.warning("Network idle timeout (mobile), proceeding with screenshot anyway")
                
            except PlaywrightTimeoutError as e:
                logger.error(f"Page load timeout for {url} (mobile): {e}")
                raise TimeoutError(f"Page load timeout after 60 seconds: {url}") from e
            except Exception as e:
                logger.error(f"Error navigating to {url} (mobile): {type(e).__name__}: {e}")
                raise RuntimeError(f"Failed to navigate to {url}: {e}") from e
            
            # Capture screenshot
            try:
                logger.debug("Capturing mobile screenshot...")
                png = page.screenshot(full_page=True, type="png")
                final_url = page.url
                title = page.title()
                logger.info(f"Mobile screenshot captured: {len(png)} bytes, final_url={final_url}, title={title[:50]}")
            except Exception as e:
                logger.error(f"Error capturing mobile screenshot: {type(e).__name__}: {e}")
                raise RuntimeError(f"Failed to capture mobile screenshot: {e}") from e
            finally:
                context.close()
                browser.close()

        # Validate screenshot
        if not isinstance(png, (bytes, bytearray)):
            raise RuntimeError(f"screenshot_invalid_type type={type(png)}")
        
        if len(png) < 10_000:
            raise RuntimeError(f"screenshot_too_small bytes={len(png)} final_url={final_url} title={title}")
        
        if not png.startswith(PNG_MAGIC):
            raise RuntimeError(f"screenshot_invalid_format bytes={len(png)} final_url={final_url} title={title}")
        
        logger.info(f"Mobile screenshot validation passed: {len(png)} bytes")
        return bytes(png)
        
    except ImportError as e:
        logger.error(f"Playwright not installed: {e}")
        raise ImportError("Playwright is not installed. Run: pip install playwright && playwright install chromium") from e
    except Exception as e:
        logger.exception(f"Unexpected error in mobile screenshot capture: {type(e).__name__}: {e}")
        raise















