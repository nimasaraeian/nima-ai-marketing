"""
Unified intake orchestrator: routes URL/IMAGE/TEXT to appropriate extractor.
"""
import logging
from typing import Optional
from fastapi import HTTPException
from api.schemas.page_map import PageMap
from api.services.intake.extractor_url import extract_from_url
from api.services.intake.extractor_image import extract_from_image
from api.services.intake.extractor_text import extract_from_text

logger = logging.getLogger(__name__)


async def build_page_map(
    url: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    text: Optional[str] = None,
    goal: str = "leads"
) -> PageMap:
    """
    Build PageMap from exactly one input source.
    
    Args:
        url: Optional URL string
        image_bytes: Optional image file bytes
        text: Optional text content
        goal: Analysis goal (default: "leads")
        
    Returns:
        PageMap instance
        
    Raises:
        HTTPException: If validation fails or extraction fails
    """
    # Validation: exactly one input
    inputs_count = sum([
        1 if url and url.strip() else 0,
        1 if image_bytes and len(image_bytes) > 0 else 0,
        1 if text and text.strip() else 0
    ])
    
    if inputs_count == 0:
        raise HTTPException(
            status_code=422,
            detail={
                "stage": "validation",
                "message": "Provide exactly one input: url, image, or text"
            }
        )
    
    if inputs_count > 1:
        raise HTTPException(
            status_code=422,
            detail={
                "stage": "validation",
                "message": "Provide exactly one input, not multiple"
            }
        )
    
    # Route to appropriate extractor
    try:
        if url and url.strip():
            logger.info(f"Extracting from URL: {url}")
            return await extract_from_url(url.strip(), goal)
        
        elif image_bytes and len(image_bytes) > 0:
            logger.info(f"Extracting from image ({len(image_bytes)} bytes)")
            return await extract_from_image(image_bytes, goal)
        
        elif text and text.strip():
            logger.info(f"Extracting from text ({len(text)} chars)")
            return await extract_from_text(text.strip(), goal)
        
        else:
            # Should not reach here due to validation above
            raise HTTPException(
                status_code=422,
                detail={
                    "stage": "validation",
                    "message": "No valid input provided"
                }
            )
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except ValueError as e:
        # Convert ValueError to HTTPException with stage info
        source = "url" if url else ("image" if image_bytes else "text")
        raise HTTPException(
            status_code=500,
            detail={
                "stage": f"{source}_extract",
                "message": str(e)
            }
        )
    except Exception as e:
        # Catch-all for other exceptions
        source = "url" if url else ("image" if image_bytes else "text")
        logger.exception(f"Extraction failed for {source}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "stage": f"{source}_extract",
                "message": f"Extraction failed: {str(e)}"
            }
        )

