"""
Canonical unified analysis endpoint: POST /api/analyze/human

Accepts URL, IMAGE, or TEXT and returns unified decision report.
"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from api.services.intake.unified_intake import build_page_map
from api.services.decision.report_from_map import report_from_page_map

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/analyze/human")
async def analyze_human(
    goal: str = Form(default="leads"),
    url: Optional[str] = Form(default=None),
    text: Optional[str] = Form(default=None),
    image: Optional[UploadFile] = File(default=None)
) -> Dict[str, Any]:
    """
    Unified analysis endpoint for URL, IMAGE, or TEXT.
    
    Accepts multipart/form-data with exactly one of:
    - url: URL string
    - text: Text content
    - image: Image file
    
    Args:
        goal: Analysis goal (leads, sales, booking, etc.)
        url: Optional URL string
        text: Optional text content
        image: Optional image file
        
    Returns:
        Response with status, mode, page_map, summary, human_report, issues_count, screenshots
    """
    try:
        # Read image bytes if provided
        image_bytes = None
        if image:
            image_bytes = await image.read()
            if len(image_bytes) == 0:
                image_bytes = None
        
        # Determine mode
        mode = None
        if url and url.strip():
            mode = "url"
        elif image_bytes and len(image_bytes) > 0:
            mode = "image"
        elif text and text.strip():
            mode = "text"
        
        if not mode:
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "stage": "validation",
                    "message": "Provide exactly one input: url, text, or image"
                }
            )
        
        # Build PageMap
        try:
            page_map = await build_page_map(
                url=url.strip() if url else None,
                image_bytes=image_bytes,
                text=text.strip() if text else None,
                goal=goal
            )
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logger.exception(f"PageMap extraction failed: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "stage": f"{mode}_extract",
                    "message": f"Extraction failed: {str(e)}"
                }
            )
        
        # Generate report from PageMap
        try:
            report = await report_from_page_map(page_map)
        except Exception as e:
            logger.exception(f"Report generation failed: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "stage": "decision_engine",
                    "message": f"Report generation failed: {str(e)}"
                }
            )
        
        # Extract summary and issues
        summary = report.get("summary") or report.get("what_to_fix_first") or "Analysis completed."
        findings = report.get("findings", {})
        top_issues = findings.get("top_issues", []) if isinstance(findings, dict) else []
        issues_count = len(top_issues) if isinstance(top_issues, list) else 0
        
        # Extract screenshots (only for URL mode)
        screenshots = None
        if mode == "url" and "screenshots" in report:
            screenshots = report.get("screenshots")
        
        # Build response
        response = {
            "status": "ok",
            "mode": mode,
            "goal": goal,
            "page_map": page_map.dict(),  # Include for debugging
            "summary": summary,
            "human_report": report.get("human_report") or report.get("report") or "",
            "issues_count": issues_count,
            "screenshots": screenshots,
            "debug": report.get("debug", {})
        }
        
        return response
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.exception(f"Unexpected error in analyze_human: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "stage": "unknown",
                "message": f"Unexpected error: {str(e)}"
            }
        )

