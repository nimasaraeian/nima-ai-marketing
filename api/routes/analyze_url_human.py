"""
Endpoint for human-readable URL analysis.
Uses Playwright to capture page, extracts DOM elements, runs heuristics,
and generates a human report via OpenAI.
"""
import sys
import asyncio
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Request as FastAPIRequest
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, Literal, Dict, Any

# Set event loop policy for Windows compatibility
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except:
        pass  # Already set or not needed

from api.services.page_capture import capture_page_artifacts
from api.services.page_extract import extract_page_map
from api.services.brain_rules import run_heuristics
from api.services.human_report import render_human_report
from api.utils.output_sanitize import normalize_response_shape, enforce_english_only, ensure_capture_attached

# Optional import for memory logging (may not be available in all environments)
try:
    from api.memory.brain_memory import log_analysis
except ImportError:
    log_analysis = None

router = APIRouter()

Goal = Literal["leads", "sales", "booking", "contact", "subscribe", "other"]
Locale = Literal["fa", "en", "tr"]


def _public_file_url(
    request: FastAPIRequest,
    abs_path: str | None,
    mount_prefix: str
) -> str | None:
    """
    Convert internal absolute path to public file URL.
    
    Uses PUBLIC_BASE_URL env var if set (production), otherwise falls back to
    request headers/base_url (local development).
    
    Args:
        request: FastAPI Request object
        abs_path: Absolute path to file (e.g., /app/api/artifacts/screenshot.png)
        mount_prefix: Mount prefix (e.g., "/api/artifacts")
    
    Returns:
        Public URL (e.g., "https://domain.com/api/artifacts/screenshot.png") or None
    """
    if not abs_path:
        return None
    
    p = Path(abs_path)
    
    # Check for PUBLIC_BASE_URL env var first (production)
    from api.core.config import get_public_base_url
    public_base_url = get_public_base_url()
    
    if public_base_url:
        # Use PUBLIC_BASE_URL (production)
        base_url = public_base_url.rstrip("/")
    else:
        # Fallback to request-based URL (local development)
        # Use x-forwarded-proto and host headers for Railway compatibility
        proto = request.headers.get("x-forwarded-proto", "http")
        host = request.headers.get("host")
        base_url = f"{proto}://{host}" if host else str(request.base_url).rstrip("/")
    
    return f"{base_url}{mount_prefix}/{p.name}"


def public_artifact_url(request: FastAPIRequest, abs_path: str | None) -> str | None:
    """
    Convert internal absolute path to public artifact URL.
    Convenience wrapper for _public_file_url with /api/artifacts prefix.
    """
    return _public_file_url(request, abs_path, "/api/artifacts")


def _get_base_url(request: FastAPIRequest) -> str:
    """
    Get base URL for making relative URLs absolute.
    
    Uses PUBLIC_BASE_URL env var if set, otherwise falls back to request base URL.
    """
    from api.core.config import get_public_base_url
    public_base_url = get_public_base_url()
    
    if public_base_url:
        return public_base_url.rstrip("/")
    else:
        # Fallback to request-based URL
        proto = request.headers.get("x-forwarded-proto", "http")
        host = request.headers.get("host")
        if host:
            return f"{proto}://{host}".rstrip("/")
        else:
            return str(request.base_url).rstrip("/")


def _make_url_absolute(url: str | None, base_url: str) -> str | None:
    """
    Make a URL absolute if it's relative (starts with "api/" or "/api/").
    
    Args:
        url: URL to make absolute (can be None)
        base_url: Base URL to prefix with
        
    Returns:
        Absolute URL or None if input was None
    """
    if not url or not isinstance(url, str):
        return url
    
    # If already absolute (starts with http:// or https://), return as-is
    if url.startswith(("http://", "https://")):
        return url
    
    # If relative (starts with "api/" or "/api/"), make absolute
    if url.startswith("api/") or url.startswith("/api/"):
        # Remove leading slash if present
        path = url.lstrip("/")
        return f"{base_url}/{path}"
    
    # Otherwise return as-is
    return url


def _normalize_screenshot_keys(result: Dict[str, Any], request: FastAPIRequest) -> Dict[str, Any]:
    """
    Normalize screenshot keys in capture.screenshots for frontend compatibility.
    
    - Adds `above_the_fold` = `desktop` if missing
    - Adds `mobile_above_the_fold` = `mobile` if missing
    - Makes URLs absolute if they start with "api/" or "/api/"
    - Adds debug info about screenshot keys
    
    Args:
        result: Response dictionary
        request: FastAPI Request object for determining base URL
        
    Returns:
        Result dictionary with normalized screenshot keys
    """
    # Ensure capture exists
    if "capture" not in result or not isinstance(result.get("capture"), dict):
        return result
    
    capture = result["capture"]
    
    # Ensure screenshots exists in capture
    if "screenshots" not in capture or not isinstance(capture.get("screenshots"), dict):
        return result
    
    screenshots = capture["screenshots"]
    
    # Get base URL for making relative URLs absolute
    base_url = _get_base_url(request)
    
    # Normalize keys: add above_the_fold and mobile_above_the_fold if missing
    if "desktop" in screenshots and "above_the_fold" not in screenshots:
        screenshots["above_the_fold"] = screenshots["desktop"]
    
    if "mobile" in screenshots and "mobile_above_the_fold" not in screenshots:
        screenshots["mobile_above_the_fold"] = screenshots["mobile"]
    
    # Make URLs absolute in all screenshot objects
    def _normalize_screenshot_object(obj: Any) -> Any:
        """Recursively normalize screenshot object URLs."""
        if isinstance(obj, dict):
            normalized = {}
            for key, value in obj.items():
                # Check if this is a URL field (contains "url" or "data_url")
                if ("url" in key.lower() or "data_url" in key.lower()) and isinstance(value, str):
                    normalized[key] = _make_url_absolute(value, base_url)
                else:
                    # Recursively process nested objects
                    normalized[key] = _normalize_screenshot_object(value)
            return normalized
        elif isinstance(obj, list):
            return [_normalize_screenshot_object(item) for item in obj]
        else:
            return obj
    
    # Normalize all screenshot objects
    screenshots = _normalize_screenshot_object(screenshots)
    capture["screenshots"] = screenshots
    
    # Add debug info
    debug = result.get("debug", {})
    if not isinstance(debug, dict):
        debug = {}
    
    debug["screenshots_keys"] = list(screenshots.keys())
    debug["screenshots_values_present"] = {
        k: bool(screenshots.get(k)) for k in screenshots.keys()
    }
    
    result["debug"] = debug
    result["capture"] = capture
    
    return result


class AnalyzeUrlHumanRequest(BaseModel):
    """Request model for human URL analysis."""
    url: str
    goal: Optional[Goal] = "other"
    locale: Optional[Locale] = "en"
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v:
            raise ValueError("URL cannot be empty")
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v


@router.get("/api/analyze/url-human/test")
async def test_endpoint():
    """Test endpoint to verify route is working."""
    return {"analysisStatus": "ok", "message": "Endpoint is accessible"}

@router.post("/api/analyze/url-human/simple")
async def analyze_url_human_simple(payload: AnalyzeUrlHumanRequest) -> Dict[str, Any]:
    """Simple test version without Playwright."""
    try:
        return {
            "analysisStatus": "ok",
            "message": "Simple test successful",
            "url": payload.url,
            "goal": payload.goal,
            "locale": payload.locale
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/analyze/url-human/test-capture")
async def test_capture_only(payload: AnalyzeUrlHumanRequest, request: FastAPIRequest) -> Dict[str, Any]:
    """Test only the capture step."""
    import os
    from api.paths import ARTIFACTS_DIR
    
    try:
        print(f"[test_capture] Starting capture for: {payload.url}")
        
        # Get base URL for artifact URLs
        base_url = _get_base_url(request)
        
        capture = await capture_page_artifacts(str(payload.url), base_url=base_url)
        
        # Extract artifacts from capture (new structure)
        artifacts = capture.get("artifacts", {})
        
        # Build capture response with new structure
        capture_response = {
            "status": capture.get("status", "ok"),
            "timestamp": capture.get("timestamp_utc"),
            "title": capture.get("dom", {}).get("title"),
            "html_length": len(capture.get("dom", {}).get("html_excerpt", "")),
            "artifacts": artifacts,  # New structure with url + data_uri
            "screenshots": capture.get("screenshots", {})  # Legacy format
        }
        
        return {
            "analysisStatus": "ok",
            "url": payload.url,
            "capture": capture_response
        }
    except Exception as e:
        import traceback
        error_detail = str(e) if str(e) else f"{type(e).__name__}: An error occurred"
        traceback.print_exc()
        
        # Check if it's an artifact missing error
        error_stage = "artifact_missing" if "ARTIFACT_MISSING" in error_detail or "ARTIFACT_INVALID" in error_detail else "capture_failed"
        
        # Return error response with analysisStatus instead of raising HTTPException
        # Include error artifacts structure (never null)
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
        
        return {
            "analysisStatus": "error",
            "url": payload.url,
            "error": {
                "message": error_detail,
                "stage": error_stage
            },
            "capture": {
                "status": "error",
                "error": error_detail,
                "artifacts": error_artifacts,
                "screenshots": {}
            }
        }

@router.post("/api/analyze/url-human", response_model=None)
async def analyze_url_human(payload: AnalyzeUrlHumanRequest, request: FastAPIRequest) -> Dict[str, Any]:
    """
    Analyze a URL and generate a human-readable report.
    
    DEPRECATED: This endpoint now internally calls the unified /api/analyze/human endpoint.
    For new integrations, use /api/analyze/human directly.
    
    Process:
    1. Capture page with Playwright (screenshots + DOM)
    2. Extract structured data (H1/H2, CTAs, trust signals)
    3. Run heuristics to find issues and quick wins
    4. Generate human-readable report via OpenAI
    
    Args:
        payload: Request with URL, goal, and locale
        
    Returns:
        Dictionary with analysis status, JSON, and human report
    """
    import logging
    logger = logging.getLogger("analyze_url_human")
    
    try:
        logger.info(f"Starting analysis for URL: {payload.url}, Goal: {payload.goal}, Locale: {payload.locale}")
        print(f"\n[analyze_url_human] Starting analysis for URL: {payload.url}")
        print(f"[analyze_url_human] Goal: {payload.goal}, Locale: {payload.locale}")
        
        # Use canonical report builder (SAME as image/text)
        from api.services.intake.unified_intake import build_page_map
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
        
        # Build PageMap from URL
        page_map = await build_page_map(
            url=payload.url,
            image_bytes=None,
            text=None,
            goal=payload.goal or "other"
        )
        
        # Generate report using canonical builder
        report = await build_human_report_from_page_map(
            page_map=page_map,
            goal=payload.goal or "other",
            locale=payload.locale or "en"
        )
        
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
        summary = report.get("summary", {})
        if not isinstance(summary, dict):
            summary = {}
        summary["issues_count"] = issues_count
        summary["quick_wins_count"] = quick_wins_count
        
        # Convert to legacy format for backward compatibility
        response_data = {
            "human_report": report.get("human_report", ""),
            "summary": summary,
            "findings": findings,
            "issues": issues,
            "quick_wins": quick_wins,
            "issues_count": issues_count,
            "quick_wins_count": quick_wins_count,
            "debug": report.get("debug", {}),
            "page_type": report.get("page_type"),
            "screenshots": report.get("screenshots", {})
        }
        
        print("[analyze_url_human] ✅ Analysis completed via canonical builder")
        
        print("[analyze_url_human] ✅ Analysis completed successfully")
        
        # Write analysis memory (Decision Brain memory) - preserve existing memory logging
        try:
            import hashlib
            from api.services.page_extract import extract_page_map
            
            # Extract data for memory from response
            human_report = response_data.get("human_report", "")
            findings = response_data.get("findings", {})
            top_issues = findings.get("top_issues", [])
            page_type = response_data.get("page_type", {})
            page_type_name = page_type.get("type", "unknown") if isinstance(page_type, dict) else str(page_type)
            
            screenshots = response_data.get("screenshots", {})
            screenshots_for_memory = {
                "desktop_atf": screenshots.get("desktop", {}).get("above_the_fold_data_url"),
                "mobile_atf": screenshots.get("mobile", {}).get("above_the_fold_data_url"),
            }
            report_hash = hashlib.sha256((human_report or "").encode("utf-8")).hexdigest()

            # Log analysis to memory if available (optional feature)
            analysis_id = None
            if log_analysis:
                analysis_id = log_analysis(
                    url=str(payload.url),
                    page_type=page_type_name,
                    ruleset_version="human_report_v2",
                    top_issues=top_issues,
                    screenshots=screenshots_for_memory,
                    decision_probability=None,
                    report_hash=report_hash,
                )
            if analysis_id:
                response_data["analysis_id"] = analysis_id
        except Exception as e:
            # Memory failures must never break the main analysis path
            logger.warning(f"[analyze_url_human] Failed to log analysis memory: {e}")
        
        # ✅ Ensure capture and screenshots are always attached (never null)
        response_data = await ensure_capture_attached(
            url=payload.url,
            goal=payload.goal or "other",
            locale=payload.locale or "en",
            result=response_data,
            request=request
        )
        
        # ✅ Normalize screenshot keys for frontend compatibility
        response_data = _normalize_screenshot_keys(response_data, request)
        
        # ✅ normalize response keys + fill summary.url
        response_data = normalize_response_shape(
            response_data,
            url=payload.url,
            locale=payload.locale or "en",
            goal=payload.goal or "other"
        )
        
        # ✅ enforce English + repair mojibake (when locale=en)
        response_data = enforce_english_only(response_data)
        
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except RuntimeError as e:
        error_str = str(e)
        # Handle LLM unavailability
        if error_str == "LLM_UNAVAILABLE":
            raise HTTPException(
                status_code=503,
                detail={
                    "type": "LLM_UNAVAILABLE",
                    "message": "Language analysis is currently unavailable. Please try again in a few minutes."
                }
            )
        # Handle English-only violation (blocking error)
        if "ENGLISH_ONLY_VIOLATION" in error_str:
            raise HTTPException(
                status_code=500,
                detail={
                    "type": "ENGLISH_ONLY_VIOLATION",
                    "message": "Report generation failed: Output contained non-English characters. This is a system error."
                }
            )
        # Re-raise other RuntimeErrors
        raise
    except Exception as e:
        import traceback
        error_type = type(e).__name__
        error_message = str(e) if str(e) else f"{error_type}: An unknown error occurred"
        error_traceback = traceback.format_exc()
        
        # Log to both logger and print
        logger.error(f"Error in analyze_url_human: {error_type}: {error_message}")
        logger.error(f"Traceback: {error_traceback}")
        print(f"\n{'='*60}")
        print(f"❌ ERROR in analyze_url_human:")
        print(f"Type: {error_type}")
        print(f"Message: {error_message}")
        print(f"Traceback:\n{error_traceback}")
        print(f"{'='*60}\n")
        
        # Write to file for debugging
        try:
            with open("api/error_log.txt", "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Error in analyze_url_human: {error_type}: {error_message}\n")
                f.write(f"Traceback:\n{error_traceback}\n")
                f.write(f"{'='*60}\n")
        except:
            pass
        
        # Raise HTTPException with detailed message
        raise HTTPException(
            status_code=500,
            detail=f"{error_type}: {error_message}"
        )


@router.post("/api/analyze/url-human/regression-test")
async def regression_test_endpoint(request: FastAPIRequest) -> Dict[str, Any]:
    """
    Regression test endpoint (local only) that tests 3 URLs and reports:
    - page_type
    - top_issues IDs
    - forbidden suggestions count
    
    URLs tested:
    - https://nekrasgroup.com/
    - https://www.digikala.com/
    - https://stripe.com/pricing
    """
    import os
    from api.services.recommendation_guardrails import count_forbidden_suggestions
    
    # Only allow in local development
    host = request.headers.get("host", "")
    if "localhost" not in host and "127.0.0.1" not in host:
        raise HTTPException(
            status_code=403,
            detail="Regression test endpoint is only available in local development"
        )
    
    test_urls = [
        "https://nekrasgroup.com/",
        "https://www.digikala.com/",
        "https://stripe.com/pricing"
    ]
    
    results = []
    
    for url in test_urls:
        try:
            print(f"[regression_test] Testing: {url}")
            
            # Capture page
            capture = await capture_page_artifacts(url)
            
            # Extract page structure
            page_map = extract_page_map(capture)
            
            # Run heuristics
            findings = run_heuristics(
                capture,
                page_map,
                goal="leads",
                locale="en",
                url=url
            )
            
            # Get page type
            page_type = findings.get("page_context", {}).get("page_type", "unknown")
            analysis_scope = findings.get("analysis_scope", "ruleset:unknown")
            
            # Get top issues IDs
            top_issues = findings.get("findings", {}).get("top_issues", [])
            issue_ids = [
                issue.get("id") 
                for issue in top_issues 
                if isinstance(issue, dict) and issue.get("id")
            ]
            
            # Count forbidden suggestions
            forbidden_counts = count_forbidden_suggestions(
                findings.get("findings", {}),
                page_type,
                page_map
            )
            
            results.append({
                "url": url,
                "page_type": page_type,
                "analysis_scope": analysis_scope,
                "top_issues_ids": issue_ids,
                "forbidden_suggestions": forbidden_counts,
                "status": "success"
            })
            
            print(f"[regression_test] ✓ {url}: {page_type}, {len(issue_ids)} issues, {forbidden_counts['total_filtered']} filtered")
            
        except Exception as e:
            print(f"[regression_test] ✗ {url}: Error - {str(e)}")
            results.append({
                "url": url,
                "page_type": None,
                "analysis_scope": None,
                "top_issues_ids": [],
                "forbidden_suggestions": {},
                "status": "error",
                "error": str(e)
            })
    
    # Print summary
    print("\n" + "="*60)
    print("REGRESSION TEST SUMMARY")
    print("="*60)
    for result in results:
        print(f"\nURL: {result['url']}")
        print(f"  Page Type: {result['page_type']}")
        print(f"  Analysis Scope: {result['analysis_scope']}")
        print(f"  Top Issues IDs: {result['top_issues_ids']}")
        print(f"  Forbidden Suggestions Filtered: {result['forbidden_suggestions'].get('total_filtered', 0)}")
        if result['status'] == "error":
            print(f"  ERROR: {result.get('error', 'Unknown error')}")
    print("\n" + "="*60)
    
    return {
        "test_status": "completed",
        "results": results,
        "summary": {
            "total_tested": len(test_urls),
            "successful": len([r for r in results if r['status'] == 'success']),
            "failed": len([r for r in results if r['status'] == 'error'])
        }
    }

