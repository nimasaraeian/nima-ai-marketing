"""
Text analysis endpoint: POST /api/analyze/text-human

Accepts text content and returns decision report.
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Form
from api.services.intake.unified_intake import build_page_map
from api.services.decision.report_from_map import report_from_page_map

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/analyze/text-human")
async def analyze_text_human(
    text: str = Form(...),
    goal: str = Form(default="leads")
) -> Dict[str, Any]:
    """
    Analyze text and generate decision report.
    
    Args:
        text: Text content to analyze
        goal: Analysis goal (leads, sales, etc.)
        
    Returns:
        Decision report with human_report, summary, findings, etc.
    """
    logger.info("TEXT ANALYSIS REQUEST RECEIVED")
    print("=" * 60)
    print("TEXT ANALYSIS REQUEST RECEIVED")
    print(f"Text length: {len(text)} chars")
    
    try:
        if not text or not text.strip():
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "stage": "validation",
                    "message": "Text field is required and cannot be empty"
                }
            )
        
        # Build PageMap from text
        try:
            page_map = await build_page_map(
                url=None,
                image_bytes=None,
                text=text.strip(),
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
                    "stage": "text_extract",
                    "message": f"Text extraction failed: {str(e)}"
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
            "mode": "text",
            "goal": goal,
            "human_report": human_report,
            "summary": summary,
            "issues": issues,
            "quick_wins": quick_wins,
            "issues_count": issues_count,
            "quick_wins_count": quick_wins_count,
            "debug": report.get("debug", {})
        }
        
        logger.info("Text analysis completed successfully")
        print("✅ Text analysis completed successfully")
        
        return response
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.exception(f"Unexpected error in analyze_text_human: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "stage": "unknown",
                "message": f"Unexpected error: {str(e)}"
            }
        )

