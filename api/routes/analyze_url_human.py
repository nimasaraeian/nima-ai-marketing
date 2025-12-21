"""
Endpoint for human-readable URL analysis.
Uses Playwright to capture page, extracts DOM elements, runs heuristics,
and generates a human report via OpenAI.
"""
import sys
import os
import asyncio
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, Literal, Dict, Any

# Set event loop policy for Windows compatibility
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except:
        pass  # Already set or not needed

from ..services.page_capture import capture_page_artifacts, SCREENSHOT_DIR
from ..services.page_extract import extract_page_map
from ..services.brain_rules import run_heuristics
from ..services.element_detection import detect_elements_in_screenshot
from ..services.signal_engine import detect_signals
from ..services.signal_report import generate_human_report
from ..services.signal_detector_v1 import build_signal_report_v1
from ..services.decision_logic_v1 import build_decision_logic_v1
from ..services.human_renderer_v1 import build_human_report_v1
from ..services.signal_report_v1 import generate_human_report_from_v1
from ..visual_trust_engine import run_visual_trust_from_bytes
from ..services.screenshot import capture_url_png_bytes
import asyncio

router = APIRouter()

Goal = Literal["leads", "sales", "booking", "contact", "subscribe", "other"]
Locale = Literal["fa", "en", "tr"]


class AnalyzeUrlHumanRequest(BaseModel):
    """Request model for human URL analysis."""
    url: str
    goal: Optional[Goal] = "other"
    locale: Optional[Locale] = "fa"
    
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
    return {"status": "ok", "message": "Endpoint is accessible"}

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
async def test_capture_only(payload: AnalyzeUrlHumanRequest) -> Dict[str, Any]:
    """Test only the capture step."""
    try:
        print(f"[test_capture] Starting capture for: {payload.url}")
        capture = await capture_page_artifacts(str(payload.url))
        return {
            "status": "ok",
            "url": payload.url,
            "capture": {
                "timestamp": capture.get("timestamp_utc"),
                "title": capture.get("dom", {}).get("title"),
                "html_length": len(capture.get("dom", {}).get("html_excerpt", "")),
                "screenshots": capture.get("screenshots", {})
            }
        }
    except Exception as e:
        import traceback
        error_detail = str(e) if str(e) else f"{type(e).__name__}: An error occurred"
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_detail)

@router.post("/api/analyze/url-human")
async def analyze_url_human(
    payload: AnalyzeUrlHumanRequest = Body(
        ...,
        example={
            "url": "https://example.com",
            "goal": "leads",
            "locale": "fa"
        }
    )
) -> Dict[str, Any]:
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
    import json
    logger = logging.getLogger("analyze_url_human")
    
    try:
        # Validate payload before processing
        try:
            _ = payload.model_dump()
        except Exception as e:
            print("❌ INVALID INPUT PAYLOAD")
            logger.error(f"Invalid payload: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid input data: {str(e)}"
            )
        
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
        
        # Step 2.5: Build Phase 1 SignalReportV1
        print("[analyze_url_human] Step 2.5: Building Phase 1 SignalReportV1...")
        
        # Get screenshot for visual trust
        shot: bytes = b""
        visual = None
        try:
            shot = await asyncio.wait_for(
                asyncio.to_thread(capture_url_png_bytes, str(payload.url)),
                timeout=30
            )
            if shot and shot.startswith(b"\x89PNG") and len(shot) > 100:
                try:
                    raw_visual = await asyncio.wait_for(
                        asyncio.to_thread(run_visual_trust_from_bytes, shot),
                        timeout=30.0
                    )
                    if isinstance(raw_visual, dict):
                        # Pass full visual trust result (includes elements, narrative, warnings)
                        visual = raw_visual.copy()
                        visual["screenshot_used"] = True
                except Exception as e:
                    logger.exception("Visual trust analysis failed: %s", e)
                    visual = {"screenshot_used": False}
        except Exception as e:
            logger.exception("Screenshot capture failed: %s", e)
            visual = {"screenshot_used": False}
        
        # Extract features from DOM
        dom = capture.get("dom", {})
        extracted_text = dom.get("readable_text_excerpt", "") or ""
        text_lower = extracted_text.lower()
        
        # Build VisualFeatures
        vf = {
            "hero_headline": None,
            "subheadline": None,
            "primary_cta_text": None,
            "primary_cta_position": None,
            "has_pricing": "pricing" in text_lower or "$" in extracted_text,
            "has_testimonials": '"' in extracted_text or "testimonial" in text_lower,
            "has_logos": "fortune 500" in text_lower or "trusted by" in text_lower,
            "has_guarantee": "guarantee" in text_lower or "money back" in text_lower,
        }
        
        # Extract headline from page_map
        headlines = page_map.get("headlines", [])
        if headlines:
            vf["hero_headline"] = headlines[0].get("text") if headlines else None
        
        # Extract primary CTA from page_map
        ctas = page_map.get("ctas", [])
        if ctas:
            primary_cta = ctas[0]
            vf["primary_cta_text"] = primary_cta.get("label")
            vf["primary_cta_position"] = "above_fold" if primary_cta.get("where", {}).get("section") == "hero" else "unknown"
        
        # Build features dict
        features = {
            "visual": vf,
            "text": {
                "key_lines": [l for l in extracted_text.splitlines() if l.strip()][:10],
            },
            "meta": {
                "url": str(payload.url),
            }
        }
        
        # Prepare DOM data for signal detector
        # Use the new fields from page_extract: kind, location, bucket
        dom_ctas = []
        for cta in ctas:
            if isinstance(cta, dict):
                dom_ctas.append({
                    "text": cta.get("text") or cta.get("label", ""),  # Prefer "text", fallback to "label"
                    "href": cta.get("href", ""),
                    "location": cta.get("location", "unknown"),  # Use location from page_extract
                    "kind": cta.get("kind", "unknown"),  # Use kind from page_extract
                    "bucket": cta.get("bucket", "secondary")  # Include bucket for categorization
                })
        
        dom_for_signals = {
            "ctas": dom_ctas,
            "has_contact": "contact" in text_lower or "@" in extracted_text,
        }
        
        # Build SignalReportV1 (Phase 1)
        signal_report_v1 = build_signal_report_v1(
            url=str(payload.url),
            input_type="url",
            features=features,
            visual=visual or {},
            dom=dom_for_signals
        )
        print(f"[analyze_url_human] Phase 1 SignalReportV1 built: {signal_report_v1.cta_count_total} CTAs, pricing={signal_report_v1.has_pricing}")
        
        # Build DecisionLogicV1 (Phase 2)
        print("[analyze_url_human] Step 3: Building Phase 2 DecisionLogicV1...")
        decision_logic = build_decision_logic_v1(signal_report_v1)
        print(f"[analyze_url_human] Phase 2 DecisionLogicV1 built: {len(decision_logic.blockers)} blockers, probability={decision_logic.decision_probability}")
        
        # Build HumanReportV1 (Phase 3)
        print("[analyze_url_human] Step 4: Building Phase 3 HumanReportV1...")
        human_report_v1 = build_human_report_v1(signal_report_v1, decision_logic)
        print("[analyze_url_human] Phase 3 HumanReportV1 built successfully")
        
        # Keep legacy report for backward compatibility
        signal_report_result = generate_human_report_from_v1(signal_report_v1)
        human_report = signal_report_result.get("human_report", "")
        report_meta = signal_report_result.get("report_meta", {})
        
        # Keep legacy signals for backward compatibility (optional)
        signals_result = await detect_signals(capture, page_map, goal=payload.goal, locale=payload.locale)
        signals = signals_result.get("signals", [])
        signals_summary = signals_result.get("summary", {})
        
        # Step 4: Run heuristics (for page_context, optional)
        print("[analyze_url_human] Step 4: Running heuristics...")
        findings = run_heuristics(
            capture,
            page_map,
            goal=payload.goal,
            locale=payload.locale
        )
        print(f"[analyze_url_human] Found {len(findings.get('findings', {}).get('top_issues', []))} issues")
        
        print("[analyze_url_human] ✅ Analysis completed successfully")
        
        # Get base URL for screenshot URLs
        base_url = os.getenv("BACKEND_URL") or os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv("RENDER_EXTERNAL_URL")
        if not base_url:
            base_url = "http://127.0.0.1:8000"
        else:
            base_url = base_url.rstrip("/")
        
        # Build screenshots response from new schema
        # capture now returns: {analysisStatus, url, screenshots: {desktop, mobile}, warnings, missing_data}
        screenshots_response = {}
        screenshots_info = capture.get("screenshots", {})
        
        # Desktop screenshot
        desktop_info = screenshots_info.get("desktop", {})
        if desktop_info.get("status") == "ok" and desktop_info.get("url"):
            # Make URL absolute if it's relative
            desktop_url = desktop_info["url"]
            if desktop_url.startswith("/"):
                desktop_url = f"{base_url}{desktop_url}"
            screenshots_response["desktop"] = {
                **desktop_info,
                "url": desktop_url
            }
        else:
            screenshots_response["desktop"] = desktop_info
        
        # Mobile screenshot
        mobile_info = screenshots_info.get("mobile", {})
        if mobile_info.get("status") == "ok" and mobile_info.get("url"):
            # Make URL absolute if it's relative
            mobile_url = mobile_info["url"]
            if mobile_url.startswith("/"):
                mobile_url = f"{base_url}{mobile_url}"
            screenshots_response["mobile"] = {
                **mobile_info,
                "url": mobile_url
            }
        else:
            screenshots_response["mobile"] = mobile_info
        
        print(f"[analyze_url_human] Screenshots - desktop: {screenshots_response.get('desktop', {}).get('status')}, mobile: {screenshots_response.get('mobile', {}).get('status')}")
        
        # Step 6: Detect elements in screenshots (evidence)
        print("[analyze_url_human] Step 6: Detecting UI elements in screenshots...")
        evidence = None
        try:
            # Determine which screenshot to use (prefer desktop, fallback to mobile)
            desktop_path = None
            mobile_path = None
            
            # Get screenshot file paths from capture result
            desktop_info = screenshots_info.get("desktop", {})
            mobile_info = screenshots_info.get("mobile", {})
            
            if desktop_info.get("status") == "ok" and desktop_info.get("path"):
                # Extract filename from path (e.g., "api/debug_shots/desktop_20240101_120000.png")
                desktop_path_str = desktop_info["path"]
                desktop_filename = desktop_path_str.split("/")[-1] if "/" in desktop_path_str else desktop_path_str
                desktop_path = SCREENSHOT_DIR / desktop_filename
                if not desktop_path.exists():
                    desktop_path = None
            
            if mobile_info.get("status") == "ok" and mobile_info.get("path"):
                mobile_path_str = mobile_info["path"]
                mobile_filename = mobile_path_str.split("/")[-1] if "/" in mobile_path_str else mobile_path_str
                mobile_path = SCREENSHOT_DIR / mobile_filename
                if not mobile_path.exists():
                    mobile_path = None
            
            # Detect elements (prefer desktop, fallback to mobile)
            evidence = None
            if desktop_path and desktop_path.exists():
                evidence = await detect_elements_in_screenshot(str(desktop_path), viewport="desktop")
                print(f"[analyze_url_human] Detected {len(evidence.get('detected_elements', [])) if evidence else 0} elements in desktop screenshot")
            elif mobile_path and mobile_path.exists():
                evidence = await detect_elements_in_screenshot(str(mobile_path), viewport="mobile")
                print(f"[analyze_url_human] Detected {len(evidence.get('detected_elements', [])) if evidence else 0} elements in mobile screenshot")
            else:
                # No screenshots available, will use evidence_from_v1
                evidence = None
                print("[analyze_url_human] No screenshots available for element detection, will use visual elements from SignalReportV1")
        except Exception as e:
            print(f"[analyze_url_human] Error detecting elements: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            # Return empty evidence on error
            evidence = {
                "viewport": "desktop",
                "image_size": [1365, 768],
                "detected_elements": []
            }
        
        # Extract legacy decision signals from findings (for backward compatibility)
        findings_data = findings.get("findings", {})
        top_issues = findings_data.get("top_issues", [])
        trust_signals_count = len(page_map.get("trust_signals", []))
        headlines_count = len(page_map.get("headlines", []))
        ctas_count = len(page_map.get("ctas", []))
        
        # Calculate clarity score (legacy)
        h1_exists = any(h.get("tag") == "h1" for h in page_map.get("headlines", []))
        clarity_issues = [issue for issue in top_issues if "clarity" in issue.get("id", "").lower() or "h1" in issue.get("id", "").lower()]
        if not h1_exists or len(clarity_issues) > 0:
            clarity_level = "Low"
        elif headlines_count >= 2 and ctas_count >= 1:
            clarity_level = "High"
        else:
            clarity_level = "Medium"
        
        # Calculate trust score (legacy)
        trust_issues = [issue for issue in top_issues if "trust" in issue.get("id", "").lower()]
        if trust_signals_count >= 3 and len(trust_issues) == 0:
            trust_level = "High"
        elif trust_signals_count >= 1 or len(trust_issues) == 0:
            trust_level = "Medium"
        else:
            trust_level = "Low"
        
        # Calculate friction score (legacy)
        high_severity_issues = [issue for issue in top_issues if issue.get("severity") == "high"]
        if len(high_severity_issues) >= 2:
            friction_level = "High"
        elif len(top_issues) >= 3:
            friction_level = "Medium"
        else:
            friction_level = "Low"
        
        # Build response with new schema
        # Get analysisStatus from capture (ok|partial|error)
        analysis_status = capture.get("analysisStatus", "error")
        warnings = capture.get("warnings", [])
        missing_data = capture.get("missing_data", [])
        
        # Build response with exact keys as specified
        # Convert SignalReportV1 to dict for response
        signal_report_v1_dict = signal_report_v1.dict()
        
        # Build evidence from SignalReportV1 (if visual evidence not available)
        evidence_from_v1 = {
            "viewport": "desktop",
            "image_size": [1365, 768],
            "detected_elements": []
        }
        
        # Extract detected_elements from signalReportV1.raw.visual.elements
        raw_dict = signal_report_v1_dict.get("raw", {}) if isinstance(signal_report_v1_dict, dict) else {}
        visual_dict = raw_dict.get("visual", {}) if isinstance(raw_dict, dict) else {}
        visual_elements = visual_dict.get("elements", []) if isinstance(visual_dict, dict) else []
        
        if visual_elements and len(visual_elements) > 0:
            # Use visual elements from raw.visual.elements
            for e in visual_elements[:12]:  # Limit to 12
                if isinstance(e, dict):
                    evidence_from_v1["detected_elements"].append({
                        "id": e.get("id", f"elem_{len(evidence_from_v1['detected_elements'])}"),
                        "type": e.get("role", "other"),
                        "role": e.get("role", "other"),
                        "text": e.get("text", ""),
                        "bbox": e.get("bbox", [0, 0, 0, 0]),
                        "approx_position": e.get("approx_position", "unknown"),
                        "confidence": (e.get("analysis", {}) or {}).get("confidence", 0.8) if isinstance(e.get("analysis"), dict) else 0.8
                    })
        else:
            # Fallback: Add CTAs as detected elements from SignalReportV1
            for cta in signal_report_v1.ctas:
                evidence_from_v1["detected_elements"].append({
                    "id": f"cta_{len(evidence_from_v1['detected_elements'])}",
                    "type": "cta",
                    "role": "primary_cta" if cta.is_primary_candidate else "secondary_cta",
                    "text": cta.text,
                    "bbox": [0, 0, 0, 0],  # Placeholder, can be enhanced later
                    "confidence": 0.9 if cta.is_primary_candidate else 0.7
                })
        
        response_data = {
            "analysisStatus": analysis_status,
            "url": str(payload.url),
            "screenshots": screenshots_response,
            "evidence": evidence if evidence and len(evidence.get("detected_elements", [])) > 0 else evidence_from_v1,
            "warnings": warnings,
            "missing_data": missing_data,
            "signalReportV1": signal_report_v1_dict,  # Phase 1 signals (primary source)
            "decisionLogicV1": decision_logic.dict(),  # Phase 2 decision logic (new)
            "humanReportV1": human_report_v1.dict(),  # Phase 3 human report (new, structured)
            # Legacy fields removed - use humanReportV1 instead
            # "human_report": human_report,  # Removed - use humanReportV1 instead
            # "reportMeta": report_meta  # Removed - use humanReportV1.quick_wins instead
        }
        
        # Optional: Add decisionSummary separately (not decisionSignalsSummary)
        if signals_summary:
            response_data["decisionSummary"] = signals_summary  # {primary_issue, secondary_issue}
        
        # Return JSONResponse with explicit UTF-8 charset
        return JSONResponse(
            content=response_data,
            media_type="application/json; charset=utf-8"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except RuntimeError as e:
        # Handle LLM unavailability
        error_str = str(e)
        if "LLM_UNAVAILABLE" in error_str:
            raise HTTPException(
                status_code=503,
                detail={
                    "type": "LLM_UNAVAILABLE",
                    "message": "تحلیل زبانی در حال حاضر در دسترس نیست. لطفاً چند دقیقه بعد دوباره تلاش کنید."
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

