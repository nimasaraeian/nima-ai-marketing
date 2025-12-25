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
        
        # Validate report is not fake/empty
        human_report = report.get("human_report") or report.get("report") or ""
        if not human_report or len(human_report.strip()) == 0:
            logger.error("Generated report is empty")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "stage": "report_validation",
                    "message": "Generated report is empty"
                }
            )
        
        # Check for fake content markers - if status is error, report should not contain these
        if report.get("status") == "error":
            fake_markers = ["CTA Recommendations", "Personas", "Decision Friction"]
            has_fake_markers = any(marker in human_report for marker in fake_markers)
            if has_fake_markers:
                logger.error("Error response contains fake report content")
                raise HTTPException(
                    status_code=500,
                    detail={
                        "status": "error",
                        "stage": "report_validation",
                        "message": "Error response should not contain report content"
                    }
                )
        
        # Check for fake content without corresponding data
        if "CTA Recommendations" in human_report and "cta_recommendations" not in report:
            logger.warning("Report contains CTA Recommendations but no cta_recommendations field")
        if "Personas" in human_report and "mindset_personas" not in report:
            logger.warning("Report contains Personas but no mindset_personas field")
        
        # Ensure report field is not null if human_report exists
        if report.get("report") is None and not human_report:
            logger.error("Report field is null and human_report is empty")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "stage": "report_validation",
                    "message": "Report field is null"
                }
            )
        
        # Extract summary and issues
        summary = report.get("summary") or report.get("what_to_fix_first") or "Analysis completed."
        findings = report.get("findings", {})
        top_issues = findings.get("top_issues", []) if isinstance(findings, dict) else []
        issues_count = len(top_issues) if isinstance(top_issues, list) else 0
        
        # Build response
        response = {
            "status": "ok",
            "mode": "image",
            "goal": goal,
            "human_report": human_report,
            "summary": summary,
            "issues_count": issues_count,
            "findings": findings,
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

