from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi.responses import Response
from playwright.sync_api import sync_playwright
from PIL import Image
from io import BytesIO
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xFF\xD8"


class DebugScreenshotIn(BaseModel):
    url: str


def capture_url_png_bytes(url: str) -> bytes:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
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


@router.post(
    "/debug/screenshot",
    responses={200: {"content": {"image/png": {}}, "description": "PNG screenshot"}}
)
def debug_screenshot(payload: DebugScreenshotIn):
    url = payload.url.strip()
    if not url:
        raise HTTPException(
            status_code=400,
            detail={
                "analysisStatus": "error",
                "errorType": "validation",
                "errorMessage": "url is required"
            }
        )
    try:
        # Capture screenshot
        raw_bytes = capture_url_png_bytes(url)
        
        # Re-encode using Pillow to ensure strict standard format
        try:
            img = Image.open(BytesIO(raw_bytes))
            # Convert to RGB (removes alpha channel if present, ensures standard format)
            img = img.convert("RGB")
            
            # Save as PNG to BytesIO
            output = BytesIO()
            img.save(output, format="PNG")
            encoded_bytes = output.getvalue()
            output.close()
            
            # Validate magic bytes
            if not encoded_bytes.startswith(PNG_MAGIC):
                logger.error("Re-encoded image does not have PNG magic bytes")
                raise RuntimeError("Re-encoding failed: invalid PNG magic bytes")
            
            # Log first 16 bytes and final length
            first_16 = encoded_bytes[:16]
            final_length = len(encoded_bytes)
            logger.info(
                "Screenshot re-encoded: first_16_bytes=%s final_length=%d",
                first_16.hex(),
                final_length
            )
            
            return Response(content=encoded_bytes, media_type="image/png")
            
        except Exception as reencode_error:
            logger.exception("Failed to re-encode screenshot: %s", reencode_error)
            # Fallback to original bytes if re-encoding fails
            logger.warning("Falling back to original screenshot bytes")
            return Response(content=raw_bytes, media_type="image/png")
            
    except Exception as e:
        logger.exception("debug_screenshot failed")
        raise HTTPException(
            status_code=502,
            detail={
                "analysisStatus": "error",
                "errorType": type(e).__name__,
                "errorMessage": str(e)[:400]
            }
        )
