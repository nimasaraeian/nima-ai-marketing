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
from api.utils.english_only import enforce_english_only, safe_en, FALLBACK_TEXTS
from api.utils.output_sanitize import deep_fix_strings, enforce_english_only as sanitize_english_only

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
        
        # Extract screenshots (ensure always an object, never null)
        screenshots = report.get("screenshots")
        if screenshots is None or not isinstance(screenshots, dict):
            # For image/text mode, return empty screenshots object
            screenshots = {
                "desktop": {
                    "above_the_fold_data_url": None,
                    "full_page_data_url": None,
                    "viewport": {"width": 1365, "height": 768},
                    "above_the_fold": None,
                    "full_page": None,
                },
                "mobile": {
                    "above_the_fold_data_url": None,
                    "full_page_data_url": None,
                    "viewport": {"width": 390, "height": 844},
                    "above_the_fold": None,
                    "full_page": None,
                }
            }
        
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
        
        # For URL mode, ensure capture and screenshots are attached
        if mode == "url" and url:
            try:
                from api.utils.output_sanitize import ensure_capture_attached
                response = await ensure_capture_attached(
                    url=url,
                    goal=goal,
                    locale=locale,
                    result=response,
                    request=request
                )
                # Update screenshots from capture if available
                if response.get("screenshots"):
                    screenshots = response["screenshots"]
            except Exception as e:
                logger.warning(f"Failed to ensure capture attached for URL mode: {e}")
                # Continue with existing screenshots
        
        # Note: issues and quick_wins are already extracted from report above
        # We don't need to override them from debug.after_heuristics as they may contain Persian
        # The report_from_page_map already provides sanitized issues and quick_wins
        
        # 🔴 جلوگیری کامل از خروج متن فارسی (حتی اگر اشتباهی تولید شد)
        # First, replace any placeholder strings with safe fallbacks
        issues = response.get("issues", [])
        if isinstance(issues, list):
            for issue in issues:
                if isinstance(issue, dict):
                    # Replace placeholder in problem field
                    if "problem" in issue:
                        issue["problem"] = safe_en(
                            issue.get("problem", ""),
                            FALLBACK_TEXTS["problem"]
                        )
                    # Replace placeholder in why_it_hurts field
                    if "why_it_hurts" in issue:
                        issue["why_it_hurts"] = safe_en(
                            issue.get("why_it_hurts", ""),
                            FALLBACK_TEXTS["why_it_hurts"]
                        )
                    # Replace placeholder in fix_steps array
                    if "fix_steps" in issue:
                        fix_steps = issue.get("fix_steps", [])
                        if isinstance(fix_steps, list):
                            fallback_steps = FALLBACK_TEXTS["fix_steps"]
                            for i, step in enumerate(fix_steps):
                                if isinstance(step, str):
                                    fix_steps[i] = safe_en(
                                        step,
                                        fallback_steps[i] if i < len(fallback_steps) else fallback_steps[0]
                                    )
                            issue["fix_steps"] = fix_steps
                    # Replace placeholder in evidence[].value
                    if "evidence" in issue:
                        evidence = issue.get("evidence", [])
                        if isinstance(evidence, list):
                            for ev in evidence:
                                if isinstance(ev, dict) and "value" in ev:
                                    ev["value"] = safe_en(
                                        ev.get("value", ""),
                                        FALLBACK_TEXTS["evidence_value"]
                                    )
                            issue["evidence"] = evidence
        
        quick_wins = response.get("quick_wins", [])
        if isinstance(quick_wins, list):
            for qw in quick_wins:
                if isinstance(qw, dict):
                    # Replace placeholder in action field
                    if "action" in qw:
                        qw["action"] = safe_en(
                            qw.get("action", ""),
                            FALLBACK_TEXTS["quick_win_action"]
                        )
                    # Replace placeholder in reason field
                    if "reason" in qw:
                        qw["reason"] = safe_en(
                            qw.get("reason", ""),
                            FALLBACK_TEXTS["quick_win_reason"]
                        )
        
        # Update response with sanitized issues and quick_wins
        response["issues"] = issues
        response["quick_wins"] = quick_wins
        
        # Rewrite non-English content instead of blanking it
        debug_dict = response.get("debug", {})
        if not isinstance(debug_dict, dict):
            debug_dict = {}
        
        # Sanitize debug to remove any Persian content (fix mojibake and remove Persian)
        debug_dict = deep_fix_strings(debug_dict)
        
        # Recursively scrub Persian from debug (especially after_heuristics.quick_wins)
        def scrub_persian_from_debug(obj: Any) -> Any:
            """Recursively remove Persian content from debug structure."""
            if isinstance(obj, str):
                # Check for Persian characters
                has_persian = any("\u0600" <= ch <= "\u06FF" or "\u0750" <= ch <= "\u077F" or "\u08A0" <= ch <= "\u08FF" for ch in obj)
                if has_persian:
                    # Replace with safe English
                    if "quick_win" in str(type(obj).__name__).lower() or "action" in str(type(obj).__name__).lower():
                        return "Quick improvement opportunity identified."
                    elif "issue" in str(type(obj).__name__).lower():
                        return "Conversion barrier detected."
                    else:
                        return "Analysis completed."
                return obj
            elif isinstance(obj, list):
                return [scrub_persian_from_debug(x) for x in obj]
            elif isinstance(obj, dict):
                return {k: scrub_persian_from_debug(v) for k, v in obj.items()}
            else:
                return obj
        
        debug_dict = scrub_persian_from_debug(debug_dict)
        
        response, stats = enforce_english_only(response, mode=mode, debug=debug_dict, page_map=page_map, summary=summary)
        
        # Ensure screenshots is never null after sanitization
        if response.get("screenshots") is None or not isinstance(response.get("screenshots"), dict):
            response["screenshots"] = {
                "desktop": {
                    "above_the_fold_data_url": None,
                    "full_page_data_url": None,
                    "viewport": {"width": 1365, "height": 768},
                    "above_the_fold": None,
                    "full_page": None,
                },
                "mobile": {
                    "above_the_fold_data_url": None,
                    "full_page_data_url": None,
                    "viewport": {"width": 390, "height": 844},
                    "above_the_fold": None,
                    "full_page": None,
                }
            }
        
        # Update debug in response
        response["debug"] = debug_dict
        
        # Prepend "Preliminary insight:" to text fields if low_confidence
        if stats.get("low_confidence", False):
            # Update issues (prepend prefix to problem, why_it_hurts, and description fields)
            issues = response.get("issues", [])
            if isinstance(issues, list):
                for i, issue in enumerate(issues):
                    if isinstance(issue, dict):
                        # Handle problem field
                        problem = issue.get("problem", "")
                        if problem and not problem.startswith("Preliminary insight:"):
                            issue["problem"] = f"Preliminary insight: {problem}"
                        
                        # Handle why_it_hurts field
                        why_it_hurts = issue.get("why_it_hurts", "")
                        if why_it_hurts and not why_it_hurts.startswith("Preliminary insight:"):
                            issue["why_it_hurts"] = f"Preliminary insight: {why_it_hurts}"
                        
                        # Handle description field (legacy)
                        desc = issue.get("description", "")
                        if desc and not desc.startswith("Preliminary insight:"):
                            issue["description"] = f"Preliminary insight: {desc}"
                    elif isinstance(issue, str):
                        # Handle string issues - convert to dict format
                        if not issue.startswith("Preliminary insight:"):
                            issues[i] = {
                                "type": "general",
                                "problem": f"Preliminary insight: {issue}",
                                "why_it_hurts": "Preliminary insight: This issue may impact conversion rates.",
                                "severity": "medium"
                            }
                response["issues"] = issues
            
            # Update quick_wins (convert description to action/reason if needed, and prepend prefix)
            quick_wins = response.get("quick_wins", [])
            if isinstance(quick_wins, list):
                for i, qw in enumerate(quick_wins):
                    if isinstance(qw, dict):
                        # Convert description to action/reason if needed
                        if "description" in qw and "action" not in qw:
                            desc = qw.get("description", "")
                            qw["action"] = desc
                            qw["reason"] = "This improvement addresses a key conversion barrier."
                            del qw["description"]
                        
                        # Prepend prefix to action if needed
                        action = qw.get("action", "")
                        if action and not action.startswith("Preliminary insight:"):
                            qw["action"] = f"Preliminary insight: {action}"
                        
                        # Prepend prefix to reason if needed
                        reason = qw.get("reason", "")
                        if reason and not reason.startswith("Preliminary insight:"):
                            qw["reason"] = f"Preliminary insight: {reason}"
                    elif isinstance(qw, str):
                        # Handle string quick_wins - convert to dict format
                        if not qw.startswith("Preliminary insight:"):
                            quick_wins[i] = {
                                "action": f"Preliminary insight: {qw}",
                                "reason": "Preliminary insight: This improvement addresses a key conversion barrier."
                            }
                response["quick_wins"] = quick_wins
            
            # Update human_report if it exists (only if not already prefixed)
            human_report = response.get("human_report", "")
            if human_report and isinstance(human_report, str) and not human_report.startswith("Preliminary insight:"):
                response["human_report"] = f"Preliminary insight: {human_report}"
        
        # Ensure debug is updated
        response["debug"] = debug_dict
        
        return response
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.exception(f"Unexpected error in analyze_human: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis pipeline failed: {str(e)}"
        )

