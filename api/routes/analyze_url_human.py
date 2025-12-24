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
        capture = await capture_page_artifacts(str(payload.url))
        
        # Get screenshot filenames from capture (new structure with desktop and mobile)
        screenshots_raw = capture.get("screenshots", {})
        desktop_screenshots = screenshots_raw.get("desktop", {})
        mobile_screenshots = screenshots_raw.get("mobile", {})
        
        # Extract filenames
        desktop_atf_filename = desktop_screenshots.get("above_the_fold")
        desktop_full_filename = desktop_screenshots.get("full_page")
        mobile_atf_filename = mobile_screenshots.get("above_the_fold")
        mobile_full_filename = mobile_screenshots.get("full_page")
        
        # Post-capture verification: Check files actually exist and are accessible
        screenshots_to_check = [
            (ARTIFACTS_DIR / desktop_atf_filename if desktop_atf_filename else None, "Desktop ATF"),
            (ARTIFACTS_DIR / desktop_full_filename if desktop_full_filename else None, "Desktop Full"),
            (ARTIFACTS_DIR / mobile_atf_filename if mobile_atf_filename else None, "Mobile ATF"),
            (ARTIFACTS_DIR / mobile_full_filename if mobile_full_filename else None, "Mobile Full"),
        ]
        
        verification_errors = []
        for screenshot_path, name in screenshots_to_check:
            if screenshot_path and not os.path.exists(str(screenshot_path)):
                verification_errors.append(f"{name} screenshot missing: {screenshot_path}")
            elif screenshot_path and os.path.getsize(str(screenshot_path)) == 0:
                verification_errors.append(f"{name} screenshot is empty: {screenshot_path}")
        
        if verification_errors:
            error_msg = "; ".join(verification_errors)
            logger.error(f"[test_capture] Artifact verification failed: {error_msg}")
            return {
                "analysisStatus": "error",
                "url": payload.url,
                "error": {
                    "message": error_msg,
                    "stage": "artifact_missing"
                },
                "capture": None
            }
        
        # Build base URL - use PUBLIC_BASE_URL if set (production), otherwise fallback to request
        from api.core.config import get_public_base_url
        public_base_url = get_public_base_url()
        
        if public_base_url:
            # Use PUBLIC_BASE_URL (production)
            base_url = public_base_url.rstrip("/")
        else:
            # Fallback to request-based URL (local development)
            # Use x-forwarded-proto and host headers for Railway compatibility
            proto = request.headers.get("x-forwarded-proto", "http")
            host = request.headers.get("host", "")
            
            # Filter out Railway internal domains (they don't work from browser)
            if host and ".railway.internal" in host:
                # Try to get Railway public domain from environment
                railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv("RAILWAY_STATIC_URL")
                if railway_domain:
                    # Remove protocol if present
                    railway_domain = railway_domain.replace("https://", "").replace("http://", "").rstrip("/")
                    host = railway_domain
                else:
                    # Fallback: remove .railway.internal suffix
                    host = host.replace(".railway.internal", "")
            
            base_url = f"{proto}://{host}" if host else str(request.base_url).rstrip("/")
        
        # Build screenshot URLs for new structure
        screenshots_response = {
            "desktop": {
                "above_the_fold": f"{base_url}/api/artifacts/{desktop_atf_filename}" if desktop_atf_filename else None,
                "full_page": f"{base_url}/api/artifacts/{desktop_full_filename}" if desktop_full_filename else None,
                "viewport": desktop_screenshots.get("viewport", {"width": 1365, "height": 768})
            },
            "mobile": {
                "above_the_fold": f"{base_url}/api/artifacts/{mobile_atf_filename}" if mobile_atf_filename else None,
                "full_page": f"{base_url}/api/artifacts/{mobile_full_filename}" if mobile_full_filename else None,
                "viewport": mobile_screenshots.get("viewport", {"width": 390, "height": 844})
            }
        }
        
        return {
            "analysisStatus": "ok",
            "url": payload.url,
            "capture": {
                "timestamp": capture.get("timestamp_utc"),
                "title": capture.get("dom", {}).get("title"),
                "html_length": len(capture.get("dom", {}).get("html_excerpt", "")),
                "screenshots": screenshots_response
            }
        }
    except Exception as e:
        import traceback
        error_detail = str(e) if str(e) else f"{type(e).__name__}: An error occurred"
        traceback.print_exc()
        
        # Check if it's an artifact missing error
        error_stage = "artifact_missing" if "ARTIFACT_MISSING" in error_detail or "ARTIFACT_INVALID" in error_detail else "capture_failed"
        
        # Return error response with analysisStatus instead of raising HTTPException
        return {
            "analysisStatus": "error",
            "url": payload.url,
            "error": {
                "message": error_detail,
                "stage": error_stage
            },
            "capture": None
        }

@router.post("/api/analyze/url-human")
async def analyze_url_human(payload: AnalyzeUrlHumanRequest, request: FastAPIRequest) -> Dict[str, Any]:
    """
    Analyze a URL and generate a human-readable report.
    
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
        
        # Step 1: Capture page artifacts
        print("[analyze_url_human] Step 1: Capturing page artifacts...")
        logger.info("Starting page capture")
        capture = await capture_page_artifacts(str(payload.url))
        logger.info("Page capture completed successfully")
        print(f"[analyze_url_human] Capture completed. Screenshots: {capture.get('screenshots', {})}")
        
        # Step 2: Extract page structure
        print("[analyze_url_human] Step 2: Extracting page structure...")
        page_map = extract_page_map(capture)
        print(f"[analyze_url_human] Extracted {len(page_map.get('headlines', []))} headlines, {len(page_map.get('ctas', []))} CTAs")
        
        # Step 3: Run heuristics (with page type detection)
        print("[analyze_url_human] Step 3: Running heuristics...")
        findings = run_heuristics(
            capture,
            page_map,
            goal=payload.goal,
            locale=payload.locale,
            url=str(payload.url)  # Pass URL for page type detection
        )
        print(f"[analyze_url_human] Found {len(findings.get('findings', {}).get('top_issues', []))} issues")
        
        # Extract page type and analysis scope
        page_type = findings.get("page_context", {}).get("page_type", "unknown")
        analysis_scope = findings.get("analysis_scope", "ruleset:unknown")
        print(f"[analyze_url_human] Detected page type: {page_type}, analysis scope: {analysis_scope}")
        
        # Apply guardrails to filter invalid recommendations
        from api.services.recommendation_guardrails import filter_invalid_recommendations
        findings_filtered = findings.copy()
        findings_filtered["findings"] = filter_invalid_recommendations(
            findings.get("findings", {}),
            page_type,
            page_map
        )
        findings = findings_filtered
        print(f"[analyze_url_human] Applied guardrails, filtered findings")
        
        # Enforce max 3 issues: rank by impact_score or severity, keep top 3
        findings_dict = findings.get("findings", {})
        top_issues = findings_dict.get("top_issues", [])
        if isinstance(top_issues, list) and len(top_issues) > 3:
            # Rank issues by impact_score (if available) or severity score
            def get_sort_key(issue: Dict[str, Any]) -> float:
                if not isinstance(issue, dict):
                    return 0.0
                # Prefer impact_score if available
                if "impact_score" in issue:
                    return float(issue.get("impact_score", 0.0))
                # Fall back to final_severity_score
                if "final_severity_score" in issue:
                    return float(issue.get("final_severity_score", 0.0))
                # Fall back to severity mapping
                severity_map = {"high": 3.0, "medium": 2.0, "low": 1.0}
                severity = str(issue.get("severity", "medium")).lower()
                return severity_map.get(severity, 2.0)
            
            # Sort descending by impact/severity
            top_issues_sorted = sorted(top_issues, key=get_sort_key, reverse=True)
            # Keep only top 3
            findings_dict["top_issues"] = top_issues_sorted[:3]
            findings["findings"] = findings_dict
            print(f"[analyze_url_human] Ranked and filtered to top 3 issues (from {len(top_issues)} total)")
        
        # Step 4: Build analysis JSON
        print("[analyze_url_human] Step 4: Building analysis JSON...")
        analysis_json = {
            "schema_version": "1.0",
            "input": {
                "url": str(payload.url),
                "goal": payload.goal,
                "locale": payload.locale
            },
            "page_context": findings.get("page_context", {}),
            "capture": capture,
            "page_map": page_map,
            "findings": findings.get("findings", {}),
            "output_policy": {
                "no_scores": True,
                "no_percentages": True,
                "tone": "direct_human",
                "max_main_issues": 3
            },
        }
        
        # Step 5: Generate human report (use locale from payload, default to English)
        print("[analyze_url_human] Step 5: Generating human report...")
        # Always use English, ignore locale parameter
        human_report = await render_human_report(analysis_json, locale="en")
        print("[analyze_url_human] Report generated successfully")
        
        # Count actual issues from findings
        top_issues = findings.get("findings", {}).get("top_issues", [])
        actual_issues_count = len(top_issues) if isinstance(top_issues, list) else 0
        
        # Count issues in human_report by looking for numbered issues (1., 2., 3., etc.)
        import re
        # Pattern to match numbered issues: "1.", "2.", "3." at start of line or after markdown header
        issue_pattern = re.compile(r'^(\d+)\.\s+\*\*', re.MULTILINE)
        report_issues = issue_pattern.findall(human_report)
        report_issues_count = len(report_issues) if report_issues else 0
        
        # If counts don't match, log warning but use findings count (source of truth)
        if report_issues_count != actual_issues_count:
            logger.warning(f"[analyze_url_human] Issue count mismatch: findings={actual_issues_count}, report={report_issues_count}")
            print(f"[analyze_url_human] ⚠️ Issue count mismatch: findings={actual_issues_count}, report={report_issues_count}")
        
        print("[analyze_url_human] ✅ Analysis completed successfully")
        
        # Screenshots now return new structure with desktop and mobile
        screenshots_raw = capture.get("screenshots", {})
        desktop_screenshots = screenshots_raw.get("desktop", {})
        mobile_screenshots = screenshots_raw.get("mobile", {})
        
        # Extract filenames
        desktop_atf_filename = desktop_screenshots.get("above_the_fold")
        desktop_full_filename = desktop_screenshots.get("full_page")
        mobile_atf_filename = mobile_screenshots.get("above_the_fold")
        mobile_full_filename = mobile_screenshots.get("full_page")
        
        # Post-capture verification: Check files actually exist and are accessible
        import os
        from api.paths import ARTIFACTS_DIR
        
        screenshots_to_check = [
            (ARTIFACTS_DIR / desktop_atf_filename if desktop_atf_filename else None, "Desktop ATF"),
            (ARTIFACTS_DIR / desktop_full_filename if desktop_full_filename else None, "Desktop Full"),
            (ARTIFACTS_DIR / mobile_atf_filename if mobile_atf_filename else None, "Mobile ATF"),
            (ARTIFACTS_DIR / mobile_full_filename if mobile_full_filename else None, "Mobile Full"),
        ]
        
        # Verify files exist and clear filenames if they don't (graceful degradation)
        verified_filenames = {}
        for key, filename, path, name in [
            ("desktop_atf", desktop_atf_filename, ARTIFACTS_DIR / desktop_atf_filename if desktop_atf_filename else None, "Desktop ATF"),
            ("desktop_full", desktop_full_filename, ARTIFACTS_DIR / desktop_full_filename if desktop_full_filename else None, "Desktop Full"),
            ("mobile_atf", mobile_atf_filename, ARTIFACTS_DIR / mobile_atf_filename if mobile_atf_filename else None, "Mobile ATF"),
            ("mobile_full", mobile_full_filename, ARTIFACTS_DIR / mobile_full_filename if mobile_full_filename else None, "Mobile Full"),
        ]:
            if filename and path and os.path.exists(str(path)) and os.path.getsize(str(path)) > 0:
                verified_filenames[key] = filename
            elif filename:
                logger.warning(f"[analyze_url_human] {name} screenshot missing or empty: {path}")
                verified_filenames[key] = None
        
        # Use verified filenames (None if file doesn't exist)
        desktop_atf_filename = verified_filenames.get("desktop_atf")
        desktop_full_filename = verified_filenames.get("desktop_full")
        mobile_atf_filename = verified_filenames.get("mobile_atf")
        mobile_full_filename = verified_filenames.get("mobile_full")
        
        # Build base URL - use PUBLIC_BASE_URL if set (production), otherwise fallback to request
        from api.core.config import get_public_base_url
        public_base_url = get_public_base_url()
        
        if public_base_url:
            # Use PUBLIC_BASE_URL (production)
            base_url = public_base_url.rstrip("/")
        else:
            # Fallback to request-based URL (local development)
            # Use x-forwarded-proto and host headers for Railway compatibility
            proto = request.headers.get("x-forwarded-proto", "http")
            host = request.headers.get("host", "")
            
            # Filter out Railway internal domains (they don't work from browser)
            if host and ".railway.internal" in host:
                # Try to get Railway public domain from environment
                railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv("RAILWAY_STATIC_URL")
                if railway_domain:
                    # Remove protocol if present
                    railway_domain = railway_domain.replace("https://", "").replace("http://", "").rstrip("/")
                    host = railway_domain
                else:
                    # Fallback: remove .railway.internal suffix
                    host = host.replace(".railway.internal", "")
            
            base_url = f"{proto}://{host}" if host else str(request.base_url).rstrip("/")
        
        # Build screenshot URLs for new structure
        screenshots_response = {
            "desktop": {
                "above_the_fold": f"{base_url}/api/artifacts/{desktop_atf_filename}" if desktop_atf_filename else None,
                "full_page": f"{base_url}/api/artifacts/{desktop_full_filename}" if desktop_full_filename else None,
                "viewport": desktop_screenshots.get("viewport", {"width": 1365, "height": 768})
            },
            "mobile": {
                "above_the_fold": f"{base_url}/api/artifacts/{mobile_atf_filename}" if mobile_atf_filename else None,
                "full_page": f"{base_url}/api/artifacts/{mobile_full_filename}" if mobile_full_filename else None,
                "viewport": mobile_screenshots.get("viewport", {"width": 390, "height": 844})
            }
        }
        
        # Limit response size - don't send full HTML/capture data
        response_data = {
            "analysisStatus": "ok",
            "human_report": human_report,
            "page_type": page_type,  # Detected page type
            "analysis_scope": analysis_scope,  # Ruleset used for analysis
            "summary": {
                "url": str(payload.url),
                "goal": payload.goal,
                "locale": payload.locale,
                "headlines_count": len(page_map.get("headlines", [])),
                "ctas_count": len(page_map.get("ctas", [])),
                "issues_count": actual_issues_count,
                "quick_wins_count": len(findings.get("findings", {}).get("quick_wins", [])),
            },
            "findings": findings.get("findings", {}),
            "capture_info": {
                "timestamp": capture.get("timestamp_utc"),
                "screenshots": screenshots_response,
                "title": capture.get("dom", {}).get("title"),
            },
            "page_map": {
                "headlines": page_map.get("headlines", []),
                "ctas": page_map.get("ctas", []),
                "trust_signals": page_map.get("trust_signals", []),
            },
            # Add public screenshots URLs at root level for easy access (new structure)
            "screenshots": screenshots_response
        }

        # Write analysis memory (Decision Brain memory)
        try:
            import hashlib

            top_issues = findings.get("findings", {}).get("top_issues", [])
            screenshots_for_memory = {
                "desktop_atf": screenshots_response.get("desktop", {}).get("above_the_fold"),
                "mobile_atf": screenshots_response.get("mobile", {}).get("above_the_fold"),
            }
            report_hash = hashlib.sha256((human_report or "").encode("utf-8")).hexdigest()

            # Log analysis to memory if available (optional feature)
            analysis_id = None
            if log_analysis:
                analysis_id = log_analysis(
                    url=str(payload.url),
                    page_type=page_type,
                    ruleset_version=analysis_scope,
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

