"""
Canonical unified analysis endpoint: POST /api/analyze/human

Accepts URL, IMAGE, or TEXT and returns unified decision report.

Supports both:
- multipart/form-data (url, text, image file, goal, locale)
- application/json (url, text, image_base64, goal, locale)
"""
import logging
import base64
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request
from api.services.intake.unified_intake import build_page_map
from api.services.decision.report_from_map import report_from_page_map
from api.utils.english_only import enforce_english_only

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/analyze/human")
async def analyze_human(request: Request) -> Dict[str, Any]:
    """
    Unified analysis endpoint for URL, IMAGE, or TEXT.
    
    Accepts both multipart/form-data and application/json with exactly one of:
    - url: URL string
    - text: Text content
    - image: Image file (multipart) or image_base64 (JSON)
    
    Args (multipart/form-data):
        goal: Analysis goal (leads, sales, booking, etc.) - default: "leads"
        locale: Locale (always forced to "en")
        url: Optional URL string
        text: Optional text content
        image: Optional image file
        
    Args (application/json):
        {
            "url": "optional URL string",
            "text": "optional text content",
            "image_base64": "optional base64-encoded image",
            "goal": "leads|sales|booking|contact|subscribe|other",
            "locale": "en (always forced to en)"
        }
        
    Returns:
        Response with status, mode, page_map, summary, human_report, issues_count, screenshots
    """
    try:
        # Parse request based on Content-Type
        content_type = request.headers.get("content-type", "").lower()
        
        url: Optional[str] = None
        text: Optional[str] = None
        image_bytes: Optional[bytes] = None
        goal: str = "leads"
        locale: str = "en"
        
        if "application/json" in content_type:
            # Parse JSON payload
            try:
                payload = await request.json()
            except Exception as e:
                logger.error(f"Failed to parse JSON: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON payload"
                )
            
            url = payload.get("url")
            if url and not isinstance(url, str):
                url = str(url)
            url = url.strip() if url else None
            
            text = payload.get("text")
            if text and not isinstance(text, str):
                text = str(text)
            text = text.strip() if text else None
            
            goal = payload.get("goal", "leads")
            if isinstance(goal, str):
                goal = goal.strip().lower() if goal else "leads"
            else:
                goal = "leads"
            
            locale = payload.get("locale", "en")
            if isinstance(locale, str):
                locale = locale.strip().lower() if locale else "en"
            else:
                locale = "en"
            
            # Handle image_base64 if provided
            image_base64 = payload.get("image_base64")
            if image_base64:
                try:
                    # Remove data URL prefix if present (e.g., "data:image/png;base64,...")
                    if "," in image_base64:
                        image_base64 = image_base64.split(",", 1)[1]
                    image_bytes = base64.b64decode(image_base64)
                    if len(image_bytes) == 0:
                        image_bytes = None
                except Exception as e:
                    logger.error(f"Failed to decode image_base64: {e}")
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid image_base64 format"
                    )
        else:
            # Parse multipart/form-data
            try:
                form = await request.form()
            except Exception as e:
                logger.error(f"Failed to parse form data: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid form data"
                )
            
            url = form.get("url")
            if isinstance(url, str):
                url = url.strip() if url else None
            else:
                url = None
            
            text = form.get("text")
            if isinstance(text, str):
                text = text.strip() if text else None
            else:
                text = None
            
            goal = form.get("goal", "leads")
            if isinstance(goal, str):
                goal = goal.strip().lower() if goal else "leads"
            else:
                goal = "leads"
            
            locale = form.get("locale", "en")
            if isinstance(locale, str):
                locale = locale.strip().lower() if locale else "en"
            else:
                locale = "en"
            
            # Handle image file
            image_file = form.get("image")
            if image_file and hasattr(image_file, "read"):
                image_bytes = await image_file.read()
                if len(image_bytes) == 0:
                    image_bytes = None
        
        # Validate and normalize goal
        valid_goals = ["leads", "sales", "booking", "contact", "subscribe", "other"]
        if isinstance(goal, str):
            goal = goal.strip().lower() if goal else "leads"
        else:
            goal = "leads"
        if goal not in valid_goals:
            goal = "other"  # Default to "other" if invalid
        
        # 🔴 اجبار کامل به انگلیسی
        locale = "en"
        
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
                detail="Provide exactly one input: url, text, or image"
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
                detail=f"Extraction failed: {str(e)}"
            )
        
        # Generate report from PageMap
        # Note: report_from_page_map now handles fake template detection with retry + fallback
        # It will never raise ValueError for fake templates - always returns a usable report
        try:
            report = await report_from_page_map(page_map)
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            # Only raise 500 for actual errors, not fake template detection
            # Fake template detection is handled internally with fallback
            error_msg = str(e)
            if "fake template" in error_msg.lower():
                logger.warning(f"Fake template error leaked through (should not happen): {e}")
                # Build minimal fallback report
                from api.services.decision.report_from_map import _build_fallback_report_from_page_map
                from api.services.brain_rules import run_heuristics
                from api.services.decision.report_from_map import _convert_page_map_to_legacy
                
                capture, page_map_dict = _convert_page_map_to_legacy(page_map)
                findings = run_heuristics(capture, page_map_dict, goal=goal, locale="en", url=None)
                ctx = {"page_type": {"type": page_map.page_type or "unknown"}}
                debug_info = {"fake_template_fallback": True, "fallback_reason": "Exception during generation"}
                report = _build_fallback_report_from_page_map(page_map, findings, ctx, debug_info)
            else:
                logger.exception(f"Report generation failed: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Report generation failed: {str(e)}"
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
            detail=f"Analysis pipeline failed: {str(e)}"
        )

