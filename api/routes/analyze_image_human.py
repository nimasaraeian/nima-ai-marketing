"""
Image analysis endpoint: POST /api/analyze/image-human

Accepts image file and returns decision report.
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from api.services.intake.unified_intake import build_page_map
from api.services.decision.report_from_map import report_from_page_map

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/analyze/image-human")
async def analyze_image_human(
    image: UploadFile = File(...),
    goal: str = Form(default="leads")
) -> Dict[str, Any]:
    """
    Analyze image and generate decision report.
    
    Args:
        image: Image file (PNG, JPG, etc.)
        goal: Analysis goal (leads, sales, etc.)
        
    Returns:
        Decision report with human_report, summary, findings, etc.
    """
    logger.info("IMAGE ANALYSIS REQUEST RECEIVED")
    print("=" * 60)
    print("IMAGE ANALYSIS REQUEST RECEIVED")
    print(f"Filename: {image.filename}")
    print(f"Content-Type: {image.content_type}")
    
    try:
        # Read image bytes
        image_bytes = await image.read()
        image_size = len(image_bytes)
        
        logger.info(f"Image size: {image_size} bytes")
        print(f"Image size: {image_size} bytes")
        
        if image_size == 0:
            logger.error("Empty image file received")
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "stage": "read_image",
                    "message": "Image file is empty"
                }
            )
        
        logger.info(f"len(image_bytes) > 0: {image_size > 0}")
        print(f"len(image_bytes) > 0: {image_size > 0}")
        
        # Build PageMap from image
        try:
            page_map = await build_page_map(
                url=None,
                image_bytes=image_bytes,
                text=None,
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
                    "stage": "image_extract",
                    "message": f"Image extraction failed: {str(e)}"
                }
            )
        
        # Generate report using canonical builder (SAME as URL)
        try:
            from api.services.decision.report_builder import build_human_report_from_page_map
        except ImportError as e:
            logger.error(f"Failed to import report_builder: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "stage": "import",
                    "message": f"Report builder module not available: {str(e)}. Please ensure api/services/decision/__init__.py exists."
                }
            )
        try:
            
            report = await build_human_report_from_page_map(
                page_map=page_map,
                goal=goal,
                locale="en"
            )
        except ValueError as ve:
            # Validation error (fake template detected or empty report)
            logger.error(f"Report validation failed: {ve}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "stage": "report_builder",
                    "message": str(ve),
                    "details": {}
                }
            )
        except Exception as e:
            logger.exception(f"Report generation failed: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "stage": "report_builder",
                    "message": f"Report generation failed: {str(e)}",
                    "details": {}
                }
            )
        
        # Report is already validated by build_human_report_from_page_map
        # Extract required fields
        human_report = report.get("human_report", "")
        summary = report.get("summary", {})
        if not isinstance(summary, dict):
            summary = {"message": str(summary) if summary else "Analysis completed."}
        
        # Extract issues and quick_wins from report
        findings = report.get("findings", {})
        if not isinstance(findings, dict):
            findings = {}
        
        issues = report.get("issues", [])
        if not issues:
            issues = findings.get("top_issues", []) if isinstance(findings, dict) else []
        if not isinstance(issues, list):
            issues = []
        
        quick_wins = report.get("quick_wins", [])
        if not quick_wins:
            quick_wins = findings.get("quick_wins", []) if isinstance(findings, dict) else []
        if not isinstance(quick_wins, list):
            quick_wins = []
        
        # Calculate counts
        issues_count = len(issues)
        quick_wins_count = len(quick_wins)
        
        # Sync summary with counts
        summary["issues_count"] = issues_count
        summary["quick_wins_count"] = quick_wins_count
        
        # Build response (ONLY include required fields, NO template fields)
        response = {
            "status": "ok",
            "mode": "image",
            "goal": goal,
            "human_report": human_report,
            "summary": summary,
            "issues": issues,
            "quick_wins": quick_wins,
            "issues_count": issues_count,
            "quick_wins_count": quick_wins_count,
            "debug": report.get("debug", {})
        }
        
        logger.info("Image analysis completed successfully")
        print("✅ Image analysis completed successfully")
        
        return response
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.exception(f"Unexpected error in analyze_image_human: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "stage": "unknown",
                "message": f"Unexpected error: {str(e)}"
            }
        )

