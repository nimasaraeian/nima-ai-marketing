"""
Canonical unified analysis endpoint: POST /api/analyze/human

Accepts URL, IMAGE, or TEXT and returns unified decision report.
"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from api.services.intake.unified_intake import build_page_map
from api.services.decision.report_from_map import report_from_page_map
from api.utils.english_only import enforce_english_only

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/analyze/human")
async def analyze_human(
    goal: str = Form(default="leads"),
    locale: str = Form(default="en"),
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
        locale: Locale (always forced to "en")
        url: Optional URL string
        text: Optional text content
        image: Optional image file
        
    Returns:
        Response with status, mode, page_map, summary, human_report, issues_count, screenshots
    """
    try:
        # Validate and normalize goal
        valid_goals = ["leads", "sales", "booking", "contact", "subscribe", "other"]
        goal = goal.strip().lower() if goal else "leads"
        if goal not in valid_goals:
            goal = "other"  # Default to "other" if invalid
        
        # 🔴 اجبار کامل به انگلیسی
        locale = "en"
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
            # 🔴 Force language to English
            page_map.language = "en"
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
        
        # Extract summary, issues, and quick_wins
        summary = report.get("summary", {})
        if not isinstance(summary, dict):
            summary = {"message": str(summary) if summary else "Analysis completed."}
        
        findings = report.get("findings", {})
        if not isinstance(findings, dict):
            findings = {}
        
        # Extract issues and quick_wins from report (they should already be at root level from report_from_page_map)
        # But also check findings as fallback
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
        
        # Extract screenshots (only for URL mode)
        screenshots = None
        if mode == "url" and "screenshots" in report:
            screenshots = report.get("screenshots")
        
        # Build response with all required fields
        response = {
            "status": "ok",
            "mode": mode,
            "goal": goal,
            "page_map": page_map.dict(),  # Include for debugging
            "summary": summary,
            "human_report": report.get("human_report") or report.get("report") or "",
            "issues": issues,
            "quick_wins": quick_wins,
            "issues_count": issues_count,
            "quick_wins_count": quick_wins_count,
            "screenshots": screenshots,
            "debug": report.get("debug", {})
        }
        
        # --- انتقال issues و quick_wins از debug به خروجی اصلی ---
        debug = response.get("debug") or {}
        after_heuristics = debug.get("after_heuristics") or {}
        
        issues = after_heuristics.get("issues", []) or []
        quick_wins = after_heuristics.get("quick_wins", []) or []
        
        # اضافه شدن به خروجی اصلی
        response["issues"] = issues
        response["quick_wins"] = quick_wins
        
        # شمارنده‌ها
        response["issues_count"] = len(issues)
        response["quick_wins_count"] = len(quick_wins)
        
        # هماهنگ‌سازی summary
        summary = response.get("summary") or {}
        summary["issues_count"] = response["issues_count"]
        summary["quick_wins_count"] = response["quick_wins_count"]
        response["summary"] = summary
        
        # 🔴 جلوگیری کامل از خروج متن فارسی (حتی اگر اشتباهی تولید شد)
        response = enforce_english_only(response)
        
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

