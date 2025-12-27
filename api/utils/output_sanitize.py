# api/utils/output_sanitize.py

from __future__ import annotations

from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)
import logging

logger = logging.getLogger(__name__)


_MOJIBAKE_MARKERS = ("Ù", "Ø", "â", "Ã", "Ð", "Þ")


def _looks_mojibake(s: str) -> bool:
    return any(m in s for m in _MOJIBAKE_MARKERS)


def fix_mojibake(s: str) -> str:
    """
    Try to repair common mojibake (UTF-8 bytes decoded as latin-1/cp1252).
    Safe: if it doesn't look mojibake, returns original.
    """
    if not isinstance(s, str):
        return s
    if not _looks_mojibake(s):
        return s
    # Common repair: latin-1 re-encode -> utf-8 decode
    try:
        repaired = s.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
        # If repair made it empty or worse, keep original
        if repaired and not _looks_mojibake(repaired):
            return repaired
        return repaired or s
    except Exception:
        return s


def deep_fix_strings(obj: Any) -> Any:
    if isinstance(obj, str):
        return fix_mojibake(obj)
    if isinstance(obj, list):
        return [deep_fix_strings(x) for x in obj]
    if isinstance(obj, dict):
        return {k: deep_fix_strings(v) for k, v in obj.items()}
    return obj


def enforce_english_only(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    If locale is en, ensure user-visible Persian doesn't leak.
    Strategy: if any Persian letters exist in key fields -> replace with safe English fallback.
    """
    locale = ((result.get("summary") or {}).get("locale") or "").lower()
    if not locale.startswith("en"):
        return result

    # Fix mojibake everywhere first
    result = deep_fix_strings(result)

    # Detect Persian characters in critical fields
    def has_persian(text: str) -> bool:
        if not isinstance(text, str):
            return False
        for ch in text:
            # Arabic/Persian Unicode blocks
            if "\u0600" <= ch <= "\u06FF" or "\u0750" <= ch <= "\u077F" or "\u08A0" <= ch <= "\u08FF":
                return True
        return False

    # Fields where Persian should never appear in EN mode
    def scrub_issue(issue: Dict[str, Any]) -> Dict[str, Any]:
        for key in ("problem", "why_it_hurts"):
            if has_persian(issue.get(key, "")):
                issue[key] = "This issue is reducing confidence near the primary CTA."
        # fix_steps
        steps = issue.get("fix_steps")
        if isinstance(steps, list) and any(has_persian(x) for x in steps if isinstance(x, str)):
            issue["fix_steps"] = [
                "Add 2–3 strong trust signals close to the primary CTA (reviews, proof, guarantees).",
                "Add one risk-reversal line (refund, trial, cancellation, or SLA).",
                "Make privacy/terms visible near the form or CTA."
            ]
        # evidence values
        ev = issue.get("evidence")
        if isinstance(ev, list):
            for e in ev:
                if isinstance(e, dict) and has_persian(e.get("value", "")):
                    e["value"] = "Trust signal not detected near the CTA."
        return issue

    # Scrub issues
    if isinstance(result.get("issues"), list):
        result["issues"] = [scrub_issue(i) if isinstance(i, dict) else i for i in result["issues"]]

    # Scrub quick_wins
    if isinstance(result.get("quick_wins"), list):
        new_qw = []
        for qw in result["quick_wins"]:
            if isinstance(qw, dict) and has_persian(qw.get("action", "")):
                qw["action"] = "Reduce CTA competition: keep one primary CTA above the fold."
                qw["reason"] = "Less choice friction, faster decisions."
            new_qw.append(qw)
        result["quick_wins"] = new_qw

    # Also scrub findings.top_issues + findings.quick_wins if present
    findings = result.get("findings")
    if isinstance(findings, dict):
        if isinstance(findings.get("top_issues"), list):
            findings["top_issues"] = [scrub_issue(i) if isinstance(i, dict) else i for i in findings["top_issues"]]
        if isinstance(findings.get("quick_wins"), list):
            patched = []
            for qw in findings["quick_wins"]:
                if isinstance(qw, dict) and has_persian(qw.get("action", "")):
                    qw["action"] = "Make the primary CTA clearer and more specific."
                    qw["reason"] = "Improves next-step clarity."
                patched.append(qw)
            findings["quick_wins"] = patched
        result["findings"] = findings

    return result


def normalize_response_shape(result: Dict[str, Any], *, url: str | None, locale: str | None, goal: str | None) -> Dict[str, Any]:
    """
    Make response keys stable for frontend: status + analysisStatus always exist.
    Also ensure summary.url is set.
    """
    # Always set these (frontend-friendly)
    if "status" not in result or result.get("status") in (None, ""):
        result["status"] = "ok"
    if "analysisStatus" not in result or result.get("analysisStatus") in (None, ""):
        # some pipelines use analysis_status; keep both if exists
        result["analysisStatus"] = result.get("analysis_status") or "ok"

    # Ensure summary exists and includes url/locale/goal
    summary = result.get("summary") or {}
    if url and not summary.get("url"):
        summary["url"] = url
    if goal and not summary.get("goal"):
        summary["goal"] = goal
    if locale and not summary.get("locale"):
        summary["locale"] = locale
    result["summary"] = summary

    # Mirror counts at top-level for convenience
    if "issues_count" not in result and isinstance(summary.get("issues_count"), int):
        result["issues_count"] = summary["issues_count"]
    if "quick_wins_count" not in result and isinstance(summary.get("quick_wins_count"), int):
        result["quick_wins_count"] = summary["quick_wins_count"]

    return result


async def ensure_capture_attached(
    url: str,
    goal: str | None,
    locale: str | None,
    result: Dict[str, Any],
    request: Any = None
) -> Dict[str, Any]:
    """
    Ensure result always has non-null capture and screenshots objects.
    
    If result already has valid capture/screenshots, keep them.
    If missing/null, run capture_page_artifacts for the URL.
    On failure, return error objects instead of null.
    
    Args:
        url: URL to capture
        goal: Analysis goal
        locale: Analysis locale
        result: Response dictionary to attach capture to
        request: FastAPI Request object (optional, for generating artifact URLs)
        
    Returns:
        Result dict with guaranteed non-null capture and screenshots
    """
    # Check if result already has valid capture/screenshots
    existing_capture = result.get("capture")
    existing_screenshots = result.get("screenshots")
    
    # Validate existing screenshots structure
    has_valid_screenshots = (
        isinstance(existing_screenshots, dict) and
        existing_screenshots.get("desktop") is not None and
        existing_screenshots.get("mobile") is not None
    )
    
    # If we have valid capture and screenshots, keep them
    if isinstance(existing_capture, dict) and has_valid_screenshots:
        # Ensure capture is not null
        if existing_capture.get("status") != "error":
            logger.info(f"[ensure_capture_attached] Using existing capture for {url}")
            return result
    
    # Need to run capture
    logger.info(f"[ensure_capture_attached] Running capture for {url}")
    
    try:
        from api.services.page_capture import capture_page_artifacts
        from api.core.config import get_public_base_url
        
        # Get base URL for artifact URLs
        base_url = None
        if request:
            try:
                # Try to get from request
                from api.routes.analyze_url_human import _get_base_url
                base_url = _get_base_url(request)
            except Exception:
                # Fallback to env var
                base_url = get_public_base_url()
        else:
            base_url = get_public_base_url()
        
        # Run capture with base_url
        capture = await capture_page_artifacts(url, base_url=base_url)
        
        # Extract artifacts and screenshots from capture (new structure)
        artifacts = capture.get("artifacts", {})
        screenshots_raw = capture.get("screenshots", {})
        
        # Ensure artifacts structure is complete
        if not artifacts or not isinstance(artifacts, dict):
            # Build minimal artifacts structure if missing
            artifacts = {
                "above_the_fold": {
                    "desktop": {
                        "filename": None,
                        "url": None,
                        "data_uri": None,
                        "width": 1365,
                        "height": 768
                    },
                    "mobile": {
                        "filename": None,
                        "url": None,
                        "data_uri": None,
                        "width": 390,
                        "height": 844
                    }
                }
            }
        
        # Build capture object with new structure
        capture_obj = {
            "status": capture.get("status", "ok"),
            "timestamp": capture.get("timestamp_utc"),
            "title": capture.get("dom", {}).get("title"),
            "html_length": len(capture.get("dom", {}).get("html_excerpt", "")),
            "artifacts": artifacts,  # New structure - always present
            "screenshots": screenshots_raw  # Legacy format for backward compat
        }
        
        # Attach to result
        result["capture"] = capture_obj
        result["screenshots"] = screenshots_raw
        
        logger.info(f"[ensure_capture_attached] ✅ Capture attached successfully for {url}")
        
    except Exception as e:
        error_detail = str(e) if str(e) else f"{type(e).__name__}: An error occurred"
        logger.error(f"[ensure_capture_attached] Capture failed for {url}: {error_detail}")
        
        # Build error response objects (never null) with new structure
        error_artifacts = {
            "above_the_fold": {
                "desktop": {
                    "filename": None,
                    "url": None,
                    "data_uri": None,
                    "width": 1365,
                    "height": 768
                },
                "mobile": {
                    "filename": None,
                    "url": None,
                    "data_uri": None,
                    "width": 390,
                    "height": 844
                }
            }
        }
        
        error_screenshots = {
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
            },
            "error": error_detail
        }
        
        error_capture = {
            "status": "error",
            "error": error_detail,
            "artifacts": error_artifacts,  # New structure
            "screenshots": error_screenshots  # Legacy format
        }
        
        # Attach error objects (never null)
        result["capture"] = error_capture
        result["screenshots"] = error_screenshots
        
        logger.warning(f"[ensure_capture_attached] Attached error capture for {url}")
    
    return result

