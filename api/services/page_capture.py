"""
Playwright-based page capture service.
Generates Desktop ATF and Mobile ATF screenshots with timestamped filenames.
Optimized for CSR (Client-Side Rendering) sites with late rendering.
"""
import os
import sys
import datetime
import asyncio
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Get project root (parent of api directory)
_project_root = Path(__file__).parent.parent.parent

# Screenshot directory from environment or default
SCREENSHOT_DEBUG_DIR = os.getenv("SCREENSHOT_DEBUG_DIR", "api/debug_shots")
SCREENSHOT_DIR = _project_root / SCREENSHOT_DEBUG_DIR

# Ensure directory exists
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# Timeout configuration
PAGE_LOAD_TIMEOUT_MS = 120_000  # 120 seconds
SCREENSHOT_TIMEOUT_MS = 60_000  # 60 seconds
NETWORKIDLE_TIMEOUT_MS = 15_000  # 15 seconds (best-effort)
FONT_LOAD_TIMEOUT_MS = 10_000  # 10 seconds
IMAGE_LOAD_TIMEOUT_MS = 15_000  # 15 seconds
MIN_SCREENSHOT_SIZE = 25_000  # 25KB - if smaller, retry


def _get_timestamp_filename(prefix: str) -> str:
    """Generate timestamped filename: prefix_YYYYMMDD_HHMMSS.png"""
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.png"


def _capture_desktop_atf(url: str, output_path: str) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """
    Capture Desktop Above the Fold screenshot with stable capture for CSR sites.
    
    Specifications:
    - viewport: 1365 × 768
    - deviceScaleFactor: 1
    - fullPage: false
    - scroll: 0
    - Two-stage wait: domcontentloaded → networkidle (best-effort)
    - Block: only media (allow stylesheet and image)
    - Wait for: fonts, viewport images
    - Fallback: re-capture if screenshot < 25KB
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str], html: Optional[str], title: Optional[str])
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    
    try:
        print(f"desktop: goto-start")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    viewport={"width": 1365, "height": 768},
                    device_scale_factor=1,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    locale="en-US",
                )
                page = context.new_page()
                page.set_default_timeout(PAGE_LOAD_TIMEOUT_MS)
                
                # A) Disable animations (prevents mid-animation capture)
                page.add_init_script("""
                    () => {
                        const style = document.createElement('style');
                        style.innerHTML = `
                            * { 
                                animation: none !important; 
                                transition: none !important; 
                                scroll-behavior: auto !important;
                                caret-color: transparent !important;
                            }
                        `;
                        document.head.appendChild(style);
                    }
                """)
                
                # Resource routing: only block media, allow stylesheet and image
                def route_handler(route):
                    rtype = route.request.resource_type
                    if rtype == "media":
                        route.abort()
                    else:
                        route.continue_()
                
                page.route("**/*", route_handler)
                
                # B) Navigation + stabilization
                # Stage 1: goto with domcontentloaded (reliable)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
                    print(f"desktop: goto-done")
                except PlaywrightTimeoutError as e:
                    print(f"desktop: error <TimeoutError: {str(e)}>")
                    return False, f"Page load timeout: {str(e)}", None, None
                except Exception as e:
                    print(f"desktop: error <{type(e).__name__}: {str(e)}>")
                    return False, f"Page load error: {type(e).__name__}: {str(e)}", None, None
                
                # Stage 2: Best-effort networkidle (do not fail if it never becomes idle)
                try:
                    page.wait_for_load_state("networkidle", timeout=NETWORKIDLE_TIMEOUT_MS)
                    print(f"desktop: networkidle-done")
                except:
                    print(f"desktop: networkidle-timeout (continuing anyway)")
                    pass
                
                # Wait for fonts to load (important for hero text)
                try:
                    page.wait_for_function(
                        "document.fonts && document.fonts.status === 'loaded'",
                        timeout=FONT_LOAD_TIMEOUT_MS
                    )
                    print(f"desktop: fonts-loaded")
                except:
                    print(f"desktop: fonts-timeout (continuing anyway)")
                    pass
                
                # Ensure top of page
                page.evaluate("window.scrollTo(0,0)")
                page.wait_for_timeout(500)
                
                # Wait for images in viewport to be complete (prevents blank hero images)
                try:
                    page.wait_for_function("""
                        () => {
                            const imgs = Array.from(document.images || []);
                            const vh = window.innerHeight || 800;
                            const inView = imgs.filter(img => {
                                const r = img.getBoundingClientRect();
                                return r.bottom > 0 && r.top < vh;
                            });
                            return inView.every(img => img.complete && img.naturalWidth > 0);
                        }
                    """, timeout=IMAGE_LOAD_TIMEOUT_MS)
                    print(f"desktop: viewport-images-loaded")
                except:
                    print(f"desktop: viewport-images-timeout (continuing anyway)")
                    pass
                
                # Small final delay for layout settle
                page.wait_for_timeout(700)
                
                # Capture screenshot
                print(f"desktop: shot-start")
                try:
                    page.screenshot(
                        path=output_path,
                        full_page=False,
                        timeout=SCREENSHOT_TIMEOUT_MS
                    )
                    
                    # Check file size - if too small, retry once
                    file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
                    if file_size < MIN_SCREENSHOT_SIZE:
                        print(f"desktop: shot-too-small ({file_size} bytes), retrying after 1500ms...")
                        page.wait_for_timeout(1500)
                        page.screenshot(
                            path=output_path,
                            full_page=False,
                            timeout=SCREENSHOT_TIMEOUT_MS
                        )
                        file_size_retry = os.path.getsize(output_path) if os.path.exists(output_path) else 0
                        print(f"desktop: shot-retry-size: {file_size_retry} bytes")
                    
                    print(f"desktop: shot-done")
                    
                    # Extract DOM content for analysis
                    html = page.content()
                    title = page.title()
                    return True, None, html, title
                except Exception as e:
                    print(f"desktop: error <{type(e).__name__}: {str(e)}>")
                    return False, f"Screenshot error: {type(e).__name__}: {str(e)}", None, None
                
            finally:
                browser.close()
                
    except Exception as e:
        error_msg = f"Desktop capture error: {type(e).__name__}: {str(e)}"
        print(f"desktop: error <{error_msg}>")
        return False, error_msg, None, None


def _capture_mobile_atf(url: str, output_path: str) -> Tuple[bool, Optional[str]]:
    """
    Capture Mobile Above the Fold screenshot with stable capture for CSR sites.
    
    Specifications:
    - viewport: 390 × 844
    - fullPage: false
    - scroll: 0
    - Two-stage wait: domcontentloaded → networkidle (best-effort)
    - Block: only media (allow stylesheet and image)
    - Wait for: fonts, viewport images
    - Fallback: re-capture if screenshot < 25KB
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    
    try:
        print(f"mobile: goto-start")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    viewport={"width": 390, "height": 844},
                    is_mobile=True,
                    has_touch=True,
                    user_agent=(
                        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                        "Version/16.0 Mobile/15E148 Safari/604.1"
                    ),
                    locale="en-US",
                )
                page = context.new_page()
                page.set_default_timeout(PAGE_LOAD_TIMEOUT_MS)
                
                # A) Disable animations (prevents mid-animation capture)
                page.add_init_script("""
                    () => {
                        const style = document.createElement('style');
                        style.innerHTML = `
                            * { 
                                animation: none !important; 
                                transition: none !important; 
                                scroll-behavior: auto !important;
                                caret-color: transparent !important;
                            }
                        `;
                        document.head.appendChild(style);
                    }
                """)
                
                # Resource routing: only block media, allow stylesheet and image
                def route_handler(route):
                    rtype = route.request.resource_type
                    if rtype == "media":
                        route.abort()
                    else:
                        route.continue_()
                
                page.route("**/*", route_handler)
                
                # B) Navigation + stabilization
                # Stage 1: goto with domcontentloaded (reliable)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
                    print(f"mobile: goto-done")
                except PlaywrightTimeoutError as e:
                    print(f"mobile: error <TimeoutError: {str(e)}>")
                    return False, f"Page load timeout: {str(e)}"
                except Exception as e:
                    print(f"mobile: error <{type(e).__name__}: {str(e)}>")
                    return False, f"Page load error: {type(e).__name__}: {str(e)}"
                
                # Stage 2: Best-effort networkidle (do not fail if it never becomes idle)
                try:
                    page.wait_for_load_state("networkidle", timeout=NETWORKIDLE_TIMEOUT_MS)
                    print(f"mobile: networkidle-done")
                except:
                    print(f"mobile: networkidle-timeout (continuing anyway)")
                    pass
                
                # Wait for fonts to load (important for hero text)
                try:
                    page.wait_for_function(
                        "document.fonts && document.fonts.status === 'loaded'",
                        timeout=FONT_LOAD_TIMEOUT_MS
                    )
                    print(f"mobile: fonts-loaded")
                except:
                    print(f"mobile: fonts-timeout (continuing anyway)")
                    pass
                
                # Ensure top of page
                page.evaluate("window.scrollTo(0,0)")
                page.wait_for_timeout(500)
                
                # Wait for images in viewport to be complete (prevents blank hero images)
                try:
                    page.wait_for_function("""
                        () => {
                            const imgs = Array.from(document.images || []);
                            const vh = window.innerHeight || 800;
                            const inView = imgs.filter(img => {
                                const r = img.getBoundingClientRect();
                                return r.bottom > 0 && r.top < vh;
                            });
                            return inView.every(img => img.complete && img.naturalWidth > 0);
                        }
                    """, timeout=IMAGE_LOAD_TIMEOUT_MS)
                    print(f"mobile: viewport-images-loaded")
                except:
                    print(f"mobile: viewport-images-timeout (continuing anyway)")
                    pass
                
                # Small final delay for layout settle
                page.wait_for_timeout(700)
                
                # Capture screenshot
                print(f"mobile: shot-start")
                try:
                    page.screenshot(
                        path=output_path,
                        full_page=False,
                        timeout=SCREENSHOT_TIMEOUT_MS
                    )
                    
                    # Check file size - if too small, retry once
                    file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
                    if file_size < MIN_SCREENSHOT_SIZE:
                        print(f"mobile: shot-too-small ({file_size} bytes), retrying after 1500ms...")
                        page.wait_for_timeout(1500)
                        page.screenshot(
                            path=output_path,
                            full_page=False,
                            timeout=SCREENSHOT_TIMEOUT_MS
                        )
                        file_size_retry = os.path.getsize(output_path) if os.path.exists(output_path) else 0
                        print(f"mobile: shot-retry-size: {file_size_retry} bytes")
                    
                    print(f"mobile: shot-done")
                    return True, None
                except Exception as e:
                    print(f"mobile: error <{type(e).__name__}: {str(e)}>")
                    return False, f"Screenshot error: {type(e).__name__}: {str(e)}"
                
            finally:
                browser.close()
                
    except Exception as e:
        error_msg = f"Mobile capture error: {type(e).__name__}: {str(e)}"
        print(f"mobile: error <{error_msg}>")
        return False, error_msg


async def capture_page_artifacts(url: str) -> Dict[str, Any]:
    """
    Capture Desktop ATF and Mobile ATF screenshots with fail-safe logic.
    
    Returns new schema:
    {
        "analysisStatus": "ok|partial|error",
        "url": "...",
        "screenshots": {
            "desktop": {
                "status": "ok|error",
                "mode": "above_fold",
                "viewport": [1365, 768],
                "path": "...",
                "url": "...",
                "error": null
            },
            "mobile": {...}
        },
        "warnings": [],
        "missing_data": []
    }
    """
    # Generate timestamped filenames
    desktop_filename = _get_timestamp_filename("desktop")
    mobile_filename = _get_timestamp_filename("mobile")
    
    desktop_path = SCREENSHOT_DIR / desktop_filename
    mobile_path = SCREENSHOT_DIR / mobile_filename
    
    # Capture screenshots in parallel (fail-safe: one can fail, other succeeds)
    loop = asyncio.get_event_loop()
    
    desktop_success, desktop_error, desktop_html, desktop_title = await loop.run_in_executor(
        None, _capture_desktop_atf, url, str(desktop_path)
    )
    
    mobile_success, mobile_error = await loop.run_in_executor(
        None, _capture_mobile_atf, url, str(mobile_path)
    )
    
    # Use desktop HTML for DOM extraction (or mobile if desktop failed)
    html = desktop_html or ""
    title = desktop_title or ""
    
    # Determine analysis status
    if desktop_success and mobile_success:
        analysis_status = "ok"
    elif desktop_success or mobile_success:
        analysis_status = "partial"
    else:
        analysis_status = "error"
    
    # Build screenshots response
    screenshots = {}
    warnings = []
    missing_data = []
    
    # Desktop screenshot
    if desktop_success and desktop_path.exists():
        screenshots["desktop"] = {
            "status": "ok",
            "mode": "above_fold",
            "viewport": [1365, 768],
            "path": f"{SCREENSHOT_DEBUG_DIR}/{desktop_filename}",
            "url": f"/{SCREENSHOT_DEBUG_DIR}/{desktop_filename}",
            "error": None
        }
    else:
        screenshots["desktop"] = {
            "status": "error",
            "mode": "above_fold",
            "viewport": [1365, 768],
            "path": None,
            "url": None,
            "error": desktop_error or "Desktop screenshot capture failed"
        }
        missing_data.append("desktop_screenshot")
        if desktop_error:
            warnings.append(f"desktop_capture_failed: {desktop_error}")
    
    # Mobile screenshot
    if mobile_success and mobile_path.exists():
        screenshots["mobile"] = {
            "status": "ok",
            "mode": "above_fold",
            "viewport": [390, 844],
            "path": f"{SCREENSHOT_DEBUG_DIR}/{mobile_filename}",
            "url": f"/{SCREENSHOT_DEBUG_DIR}/{mobile_filename}",
            "error": None
        }
    else:
        screenshots["mobile"] = {
            "status": "error",
            "mode": "above_fold",
            "viewport": [390, 844],
            "path": None,
            "url": None,
            "error": mobile_error or "Mobile screenshot capture failed"
        }
        missing_data.append("mobile_screenshot")
        if mobile_error:
            warnings.append(f"mobile_capture_failed: {mobile_error}")
    
    # Keep DOM excerpt for backward compatibility with extract_page_map
    html_excerpt = html[:25000] if html else ""
    readable_excerpt = ""
    if html:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            readable_excerpt = soup.get_text()[:20000] if soup else ""
        except:
            pass
    
    return {
        "analysisStatus": analysis_status,
        "url": url,
        "screenshots": screenshots,
        "warnings": warnings,
        "missing_data": missing_data,
        "dom": {
            "title": title,
            "html_excerpt": html_excerpt,
            "readable_text_excerpt": readable_excerpt
        }
    }
