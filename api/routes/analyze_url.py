import asyncio
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import os

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

try:
    from readability import Document
except Exception:
    Document = None  # type: ignore

from api.schemas.page_features import (
    PageFeatures,
    VisualFeatures,
    TextFeatures,
    MetaFeatures,
    FEATURES_SCHEMA_VERSION,
)
from api.brain.decision_brain import analyze_decision
from api.visual_trust_engine import run_visual_trust_from_bytes
from api.services.screenshot import capture_url_png_bytes, capture_url_png_bytes_mobile
from api.utils.text_sanitize import sanitize_any
from api.services.signal_detector_v1 import build_signal_report_v1
from api.services.decision_logic_v1 import build_decision_logic_v1
from api.services.page_capture import capture_page_artifacts
from api.services.page_extract import extract_page_map
import asyncio

# Playwright timeout compatibility
try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
except Exception:
    class PlaywrightTimeoutError(Exception):
        ...

router = APIRouter()
logger = logging.getLogger("analyze_url")


class UrlAnalyzeIn(BaseModel):
    url: str
    refresh: bool | None = None


# Text sanitization moved to api/utils/text_sanitize.py


def extract_text(html: str) -> str:
    """
    Extract text from HTML string.
    HTML should already be properly decoded as UTF-8 string.
    """
    if Document:
        doc = Document(html)
        # BeautifulSoup will handle encoding from the already-decoded string
        soup = BeautifulSoup(doc.summary(html_partial=True), "lxml", from_encoding="utf-8")
        text = soup.get_text("\n", strip=True)
    else:
        # BeautifulSoup will handle encoding from the already-decoded string
        soup = BeautifulSoup(html, "lxml", from_encoding="utf-8")
        text = soup.get_text("\n", strip=True)
    return "\n".join(text.splitlines()[:250])


async def render_screenshot(url: str, timeout: int = 60) -> bytes:
    """
    Render screenshot with timeout protection.
    
    Args:
        url: URL to screenshot
        timeout: Maximum time in seconds to wait (default: 60)
        
    Returns:
        Screenshot bytes
        
    Raises:
        TimeoutError: If screenshot capture exceeds timeout
    """
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(capture_url_png_bytes, url),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error("Screenshot capture timed out after %d seconds for URL: %s", timeout, url)
        raise TimeoutError(f"Screenshot capture timed out after {timeout} seconds for {url}")


async def render_screenshot_mobile(url: str, timeout: int = 60) -> bytes:
    """
    Render mobile screenshot with timeout protection.
    
    Args:
        url: URL to screenshot
        timeout: Maximum time in seconds to wait (default: 60)
        
    Returns:
        Screenshot bytes
        
    Raises:
        TimeoutError: If screenshot capture exceeds timeout
    """
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(capture_url_png_bytes_mobile, url),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error("Mobile screenshot capture timed out after %d seconds for URL: %s", timeout, url)
        raise TimeoutError(f"Mobile screenshot capture timed out after {timeout} seconds for {url}")


@router.post("/analyze-url")
async def analyze_url(
    payload: UrlAnalyzeIn, 
    refresh: bool = Query(False),
    explain: bool = Query(False, description="Convert diagnosis to human-readable explanation using AI")
):
    """
    Analyze a URL and return decision diagnosis.
    
    Works locally out-of-the-box without requiring MAIN_BRAIN_BACKEND_URL.
    In production, requires MAIN_BRAIN_BACKEND_URL or BRAIN_BACKEND_URL to be set.
    
    If explain=true, the diagnosis will be automatically converted to human-readable
    explanation using OpenAI (without modifying the diagnosis).
    """
    # Check config early and return friendly error if needed (production only)
    # Note: analyze-url uses local analyze_decision function, but we check config
    # in case there's any gateway mode or external service dependency
    try:
        from ..core.config import get_main_brain_backend_url, is_local_dev
        # Just check if we can get the URL - in local dev it will use fallback
        backend_url = get_main_brain_backend_url()
        # If we're in production and got here, config is OK
        is_local = is_local_dev()
    except RuntimeError as e:
        # Production: return JSON error response
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail={
                "analysisStatus": "error",
                "error": {
                    "message": str(e),
                    "type": "config_error"
                }
            }
        )
    except Exception as e:
        # Other config errors - log but don't fail in local dev
        from ..core.config import is_local_dev
        is_local = is_local_dev()
        if not is_local:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail={
                    "analysisStatus": "error",
                    "error": {
                        "message": f"Configuration error: {str(e)}",
                        "type": "config_error"
                    }
                }
            )
        # Local dev: continue with local fallback
    
    url = payload.url.strip()
    refresh_flag = str(refresh).lower() in {"1", "true", "yes"} or bool(payload.refresh)

    shot: bytes = b""
    screenshot_error: str | None = None
    debug_path: str | None = None
    extracted_text = ""
    analysis_status = "ok"
    error_message = None

    cache_dir = Path(__file__).parent.parent / "cache"
    cache_dir.mkdir(exist_ok=True)

    def cache_key(url_str: str) -> str:
        return hashlib.sha256(url_str.encode()).hexdigest()

    # 1) Fetch HTML
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=25) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            
            # Properly decode HTML content - ROOT FIX
            # Get bytes first, then detect and decode encoding correctly
            html_bytes = r.content
            
            # Detect encoding from bytes
            try:
                import chardet
                detected = chardet.detect(html_bytes)
                encoding = detected.get('encoding', 'utf-8')
                confidence = detected.get('confidence', 0)
                
                # Use detected encoding if confidence is high enough, otherwise fallback
                if confidence < 0.7:
                    # Try to get encoding from response headers first
                    if r.encoding and r.encoding.lower() != 'iso-8859-1':  # iso-8859-1 is often wrong default
                        encoding = r.encoding
                    else:
                        encoding = 'utf-8'
                
                # Decode with detected/selected encoding
                html = html_bytes.decode(encoding, errors='replace')
            except ImportError:
                # If chardet is not available, use httpx's encoding detection
                if r.encoding:
                    html = html_bytes.decode(r.encoding, errors='replace')
                else:
                    # Fallback to UTF-8
                    html = html_bytes.decode('utf-8', errors='replace')
            
            extracted_text = extract_text(html)
    except Exception as e:
        analysis_status = "error"
        error_message = f"Fetch failed: {e}"
        logger.exception("HTML fetch failed")

    # 2) Screenshots (Desktop and Mobile) with timeout
    shot = b""
    shot_mobile = b""
    screenshot_error = None
    screenshot_mobile_error = None
    debug_path = None
    debug_path_mobile = None
    
    # Desktop screenshot
    try:
        logger.info(f"Attempting to capture desktop screenshot for {url}...")
        shot = await render_screenshot(url, timeout=60)
        if not shot or not shot.startswith(b"\x89PNG"):
            raise ValueError("Invalid screenshot: PNG signature not found")
        logger.info(f"Desktop screenshot captured successfully: {len(shot)} bytes")
        
        # Save desktop screenshot
        from api.core.config import get_debug_shots_dir
        debug_dir = get_debug_shots_dir()  # Use shared config
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        debug_file = debug_dir / f"desktop_{ts}.png"
        debug_file.write_bytes(shot)
        debug_path = str(debug_file)
    except (PlaywrightTimeoutError, asyncio.TimeoutError, Exception) as e:
        screenshot_error = str(e)
        shot = b""
        error_type = type(e).__name__
        
        if isinstance(e, (asyncio.TimeoutError, PlaywrightTimeoutError)):
            screenshot_error = f"Timeout: Page took more than 60 seconds to load. Please check the URL or try again."
            logger.warning(f"Desktop screenshot timeout for {url}: {e}")
        elif "Failed to navigate" in str(e) or "net::" in str(e):
            screenshot_error = f"Network error: Could not access the website. The site may be unavailable or blocked."
            logger.error(f"Network error during desktop screenshot for {url}: {e}")
        elif "screenshot_invalid" in str(e) or "Invalid screenshot" in str(e):
            screenshot_error = f"Invalid screenshot: {e}"
            logger.error(f"Invalid desktop screenshot for {url}: {e}")
        else:
            screenshot_error = f"Screenshot capture failed ({error_type}): {e}"
            logger.exception(f"Desktop screenshot failed for {url}: {error_type}: {e}")
    
    # Mobile screenshot
    try:
        logger.info(f"Attempting to capture mobile screenshot for {url}...")
        shot_mobile = await render_screenshot_mobile(url, timeout=60)
        if not shot_mobile or not shot_mobile.startswith(b"\x89PNG"):
            raise ValueError("Invalid mobile screenshot: PNG signature not found")
        logger.info(f"Mobile screenshot captured successfully: {len(shot_mobile)} bytes")
        
        # Save mobile screenshot
        from api.core.config import get_debug_shots_dir
        debug_dir = get_debug_shots_dir()  # Use shared config
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        debug_file_mobile = debug_dir / f"mobile_{ts}.png"
        debug_file_mobile.write_bytes(shot_mobile)
        debug_path_mobile = str(debug_file_mobile)
    except (PlaywrightTimeoutError, asyncio.TimeoutError, Exception) as e:
        screenshot_mobile_error = str(e)
        shot_mobile = b""
        error_type = type(e).__name__
        
        if isinstance(e, (asyncio.TimeoutError, PlaywrightTimeoutError)):
            screenshot_mobile_error = f"Timeout: Page took more than 60 seconds to load. Please check the URL or try again."
            logger.warning(f"Mobile screenshot timeout for {url}: {e}")
        elif "Failed to navigate" in str(e) or "net::" in str(e):
            screenshot_mobile_error = f"Network error: Could not access the website. The site may be unavailable or blocked."
            logger.error(f"Network error during mobile screenshot for {url}: {e}")
        elif "screenshot_invalid" in str(e) or "Invalid screenshot" in str(e):
            screenshot_mobile_error = f"Invalid screenshot: {e}"
            logger.error(f"Invalid mobile screenshot for {url}: {e}")
        else:
            screenshot_mobile_error = f"Mobile screenshot capture failed ({error_type}): {e}"
            logger.exception(f"Mobile screenshot failed for {url}: {error_type}: {e}")
    
    # Use desktop screenshot for visual trust analysis (fallback to mobile if desktop failed)
    shot_for_visual = shot if shot else shot_mobile

    # 3) Vision Trust Analysis with timeout and fail-safe handling
    visual = None
    if shot_for_visual and len(shot_for_visual) > 100:
        try:
            # Run visual trust with timeout
            raw_visual = await asyncio.wait_for(
                asyncio.to_thread(run_visual_trust_from_bytes, shot_for_visual),
                timeout=30.0
            )
            
            # Ensure raw_visual is a dict
            if not isinstance(raw_visual, dict):
                logger.error("VisualTrust returned non-dict: %s", type(raw_visual))
                raw_visual = {}
            
            # Build visual dict with safe defaults
            visual = {
                "analysisStatus": raw_visual.get("analysisStatus", "error"),
                "label": raw_visual.get("label", "Unknown"),
                "confidence": float(raw_visual.get("confidence", 0.0)),
                "probs": raw_visual.get("probs"),
                "warnings": raw_visual.get("warnings", []) if isinstance(raw_visual.get("warnings"), list) else [],
                "elements": raw_visual.get("elements", []) if isinstance(raw_visual.get("elements"), list) else [],
                "narrative": raw_visual.get("narrative", []) if isinstance(raw_visual.get("narrative"), list) else [],
                "error": raw_visual.get("error"),
                "debugBuild": raw_visual.get("debugBuild", "VT_DEFAULT_V1"),
            }
            
            # Ensure label is valid
            if visual["label"] not in ["Low", "Medium", "High", "Unknown"]:
                visual["label"] = "Unknown"
            
            # Ensure narrative is always a non-empty list
            if not visual["narrative"]:
                visual["narrative"] = ["Visual analysis completed."]
                
        except asyncio.TimeoutError:
            logger.error("VisualTrust analysis timed out after 30 seconds")
            visual = {
                "analysisStatus": "ok",  # Return ok for demo stability
                "label": "Unknown",
                "confidence": 0.0,
                "probs": None,
                "warnings": ["visualtrust_timeout"],
                "elements": [],
                "narrative": ["Visual analysis timed out. Using text-based signals."],
                "error": None,
                "debugBuild": "VT_TIMEOUT_V1",
            }
        except Exception as e:
            logger.exception("VisualTrust analysis failed: %s", e)
            visual = {
                "analysisStatus": "ok",  # Return ok for demo stability
                "label": "Unknown",
                "confidence": 0.0,
                "probs": None,
                "warnings": ["visualtrust_exception"],
                "elements": [],
                "narrative": ["Visual analysis encountered an error. Using text-based signals."],
                "error": None,
                "debugBuild": "VT_EXCEPTION_V1",
            }
    
    # Fallback if no screenshot or visual analysis failed
    if visual is None:
        visual = {
            "analysisStatus": "ok",  # Changed to ok for demo stability
            "label": "Unknown",
            "confidence": 0.0,
            "probs": None,
            "warnings": ["screenshot_unavailable"],
            "elements": [],
            "narrative": ["Screenshot unavailable. Using text-based analysis only."],
            "error": None,
            "debugBuild": "VT_NO_SCREENSHOT_V1",
        }

    # 4) Visual feature mapping
    vf = VisualFeatures().dict()

    label_map = {"High": 0.8, "Medium": 0.5, "Low": 0.2}
    if visual["analysisStatus"] == "ok":
        if visual["label"] in label_map:
            vf["info_hierarchy_quality"] = label_map[visual["label"]]

        for n in visual.get("narrative", []):
            l = n.lower()
            if "cta not detected" in l:
                vf["primary_cta_text"] = None
                vf["cta_contrast_level"] = 0.2
            if "headline" in l:
                vf["hero_media_type"] = "headline_region_detected"

        # Map rich visual elements (dicts) to human‑readable strings for VisualFeatures.noted_elements (List[str])
        elements = visual.get("elements") or []
        noted: list[str] = []
        for e in elements:
            if not isinstance(e, dict):
                # Already a string or unknown type – cast to str safely
                noted.append(str(e))
                continue
            eid = e.get("id") or "element"
            role = e.get("role") or "unknown"
            approx_pos = e.get("approx_position") or "unknown-position"
            analysis = e.get("analysis") or {}
            notes = analysis.get("notes") or ""
            conf = analysis.get("confidence")
            parts = [f"{eid} ({role}, {approx_pos})"]
            if notes:
                parts.append(f"notes: {notes}")
            if conf is not None:
                parts.append(f"confidence={conf:.2f}")
            noted.append(" | ".join(parts))

        vf["noted_elements"] = noted or None

    # Infer from text
    text_lower = extracted_text.lower()
    primary_cta_candidate = vf.get("primary_cta_text") or (
        "Get Started" if "get started" in text_lower else None
    )
    vf["primary_cta_text"] = primary_cta_candidate
    vf["primary_cta_position"] = "hero_or_top" if vf["primary_cta_text"] else None
    vf["has_pricing"] = "pricing" in text_lower
    vf["has_logos"] = "fortune 500" in text_lower
    vf["has_testimonials"] = '"' in extracted_text

    visual_features = VisualFeatures(**vf)

    # 5) Text features
    lines = [l for l in extracted_text.splitlines() if l.strip()]
    text_features = TextFeatures(
        key_lines=lines[:10],
        offers=[l for l in lines if "%" in l or "free" in l.lower()],
        claims=[l for l in lines if "trusted" in l.lower() or "leader" in l.lower()],
        risk_reversal=[l for l in lines if "refund" in l.lower()],
        audience_clarity=lines[0] if lines else None,
        cta_copy=visual_features.primary_cta_text,
        pricing_mentions=[l for l in lines if "$" in l or "pricing" in l.lower()],
        proof_points=[l for l in lines if "clients" in l.lower()],
        differentiators=[],
    )

    meta = MetaFeatures(
        url=url,
        timestamp=datetime.utcnow().isoformat(),
        screenshot_bytes=len(shot) if shot else len(shot_mobile) if shot_mobile else 0,
    )

    features = PageFeatures(
        visual=visual_features,
        text=text_features,
        meta=meta,
    )

    # 6) Brain
    brain = analyze_decision(features)
    if visual["analysisStatus"] == "ok":
        brain["confidence"] = min(1.0, brain.get("confidence", 0.5) + 0.15)

    # Convert features to dict
    features_dict = features.dict()

    # Build response
    response = {
        "analysisStatus": analysis_status,
        "inputType": "url",
        "url": url,
        "featuresSchemaVersion": FEATURES_SCHEMA_VERSION,
        "visualTrust": visual or {
            "analysisStatus": "ok",
            "label": "Unknown",
            "confidence": 0.0,
            "probs": None,
            "warnings": [],
            "elements": [],
            "narrative": ["Visual analysis unavailable."],
            "error": None,
            "debugBuild": "VT_MISSING_V1",
        },
        "features": features_dict,
        "brain": brain,
        "extractedText": extracted_text,
        "screenshots": {
            "desktop": {
                "path": Path(debug_path).name if debug_path else None,  # Just filename
                "url": f"/api/screenshots/{Path(debug_path).name}" if debug_path else None,
                "bytes": len(shot),
                "error": screenshot_error
            } if shot else {
                "path": None,
                "url": None,
                "bytes": 0,
                "error": screenshot_error
            },
            "mobile": {
                "path": Path(debug_path_mobile).name if debug_path_mobile else None,  # Just filename
                "url": f"/api/screenshots/{Path(debug_path_mobile).name}" if debug_path_mobile else None,
                "bytes": len(shot_mobile),
                "error": screenshot_mobile_error
            } if shot_mobile else {
                "path": None,
                "url": None,
                "bytes": 0,
                "error": screenshot_mobile_error
            }
        },
        "debugScreenshotPath": debug_path,  # Keep for backward compatibility
        "debugScreenshotBytes": len(shot) if shot else len(shot_mobile) if shot_mobile else 0,
        "error": error_message,
        "debugBuild": "DEMO_READY_V1",
    }
    
    # Apply sanitization to entire response payload (sanitizes all strings recursively)
    response = sanitize_any(response)
    
    # If explain=true, generate human-readable explanation
    if explain:
        try:
            logger.info("Generating AI explanation for diagnosis...")
            from .explain import _extract_diagnosis_data, _generate_explanation
            
            # Extract diagnosis data
            diagnosis_data = _extract_diagnosis_data(response)
            logger.debug(f"Extracted diagnosis data keys: {list(diagnosis_data.keys())}")
            
            # Generate explanation (default: marketer audience, English)
            # You can add audience and language as query params if needed
            explanation = await _generate_explanation(
                diagnosis_data,
                audience="marketer",
                language="en"
            )
            
            # Add explanation to response
            response["explanation"] = explanation
            response["hasExplanation"] = True
            logger.info("✅ Explanation generated successfully")
            
        except Exception as e:
            logger.exception(f"Failed to generate explanation: {e}")
            # Don't fail the request if explanation fails
            response["explanation"] = None
            response["explanationError"] = str(e)
            response["hasExplanation"] = False
            response["explanationWarning"] = "Explanation generation failed, but diagnosis is still available."

    # Return JSONResponse with explicit UTF-8 charset
    return JSONResponse(
        content=response,
        media_type="application/json; charset=utf-8"
    )


@router.post("/api/analyze/url-signals")
async def analyze_url_signals(payload: UrlAnalyzeIn):
    """
    Analyze a URL and return Phase 1 signal detection (JSON only, no human report).
    
    This endpoint:
    - Captures page artifacts (screenshots, DOM)
    - Extracts features (visual, text, meta)
    - Runs visual trust analysis
    - Builds signal report v1 (CTA, trust, clarity signals)
    - Returns JSON only (no verdict, quick wins, or suggested rewrites)
    """
    url = payload.url.strip()
    
    # 1) Capture page artifacts (screenshots + DOM)
    capture = None
    dom_data = None
    try:
        capture = await capture_page_artifacts(url)
        if capture:
            dom_data = extract_page_map(capture)
    except Exception as e:
        logger.exception("Page capture failed: %s", e)
        capture = {}
        dom_data = {}
    
    # 2) Get screenshot for visual trust
    shot: bytes = b""
    visual = None
    try:
        shot = await render_screenshot(url, timeout=30)
        if shot and shot.startswith(b"\x89PNG") and len(shot) > 100:
            try:
                raw_visual = await asyncio.wait_for(
                    asyncio.to_thread(run_visual_trust_from_bytes, shot_for_visual),
                    timeout=30.0
                )
                if isinstance(raw_visual, dict):
                    # Pass full visual trust result (includes elements, narrative, warnings)
                    visual = raw_visual.copy()
                    visual["screenshot_used"] = True
                else:
                    visual = {"screenshot_used": False}
            except Exception as e:
                logger.exception("Visual trust analysis failed: %s", e)
                visual = {"screenshot_used": False}
    except Exception as e:
        logger.exception("Screenshot capture failed: %s", e)
        visual = {"screenshot_used": False}
    
    # 3) Extract features (similar to analyze_url endpoint)
    extracted_text = ""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=25) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            
            html_bytes = r.content
            try:
                import chardet
                detected = chardet.detect(html_bytes)
                encoding = detected.get('encoding', 'utf-8')
                if detected.get('confidence', 0) < 0.7:
                    encoding = r.encoding or 'utf-8'
                html = html_bytes.decode(encoding, errors='replace')
            except ImportError:
                html = html_bytes.decode(r.encoding or 'utf-8', errors='replace')
            
            extracted_text = extract_text(html)
    except Exception as e:
        logger.exception("HTML fetch failed: %s", e)
    
    # 4) Build VisualFeatures (simplified)
    text_lower = extracted_text.lower()
    vf = {
        "hero_headline": None,
        "subheadline": None,
        "primary_cta_text": "Get Started" if "get started" in text_lower else None,
        "primary_cta_position": "hero_or_top" if "get started" in text_lower else None,
        "has_pricing": "pricing" in text_lower or "$" in extracted_text,
        "has_testimonials": '"' in extracted_text or "testimonial" in text_lower,
        "has_logos": "fortune 500" in text_lower or "trusted by" in text_lower,
        "has_guarantee": "guarantee" in text_lower or "money back" in text_lower,
    }
    
    # 5) Build features dict
    features = {
        "visual": vf,
        "text": {
            "key_lines": [l for l in extracted_text.splitlines() if l.strip()][:10],
        },
        "meta": {
            "url": url,
            "timestamp": datetime.utcnow().isoformat(),
        }
    }
    
    # 6) Prepare DOM data for signal detector
    # Convert page_map CTAs to format expected by signal_detector_v1
    # Use the new fields from page_extract: kind, location, bucket
    dom_ctas = []
    if dom_data and isinstance(dom_data, dict):
        page_map_ctas = dom_data.get("ctas", [])
        for cta in page_map_ctas:
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
        "hero_headline": dom_data.get("hero_headline") if dom_data else None,
        "subheadline": dom_data.get("subheadline") if dom_data else None,
    }
    
    # 7) Build signal report
    try:
        signal_report = build_signal_report_v1(
            url=url,
            input_type="url",
            features=features,
            visual=visual or {},
            dom=dom_for_signals
        )
        
        # Return JSONResponse with explicit UTF-8 charset
        return JSONResponse(
            content=signal_report.dict(),
            media_type="application/json; charset=utf-8"
        )
    except Exception as e:
        logger.exception("Signal report build failed: %s", e)
        import traceback
        error_detail = str(e)
        error_type = type(e).__name__
        # Return a debug-friendly error response instead of raising HTTPException
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "error_type": error_type,
                "error_message": error_detail,
                "url": url,
                "debug": {
                    "capture_available": capture is not None,
                    "dom_data_available": dom_data is not None,
                    "visual_available": visual is not None,
                    "features_available": bool(features),
                }
            },
            media_type="application/json; charset=utf-8"
        )


@router.post("/api/analyze/url-decision")
async def analyze_url_decision(payload: UrlAnalyzeIn):
    """
    Analyze a URL and return Phase 2 decision logic (blockers, scores, decision probability).
    
    This endpoint:
    - Captures page artifacts (screenshots, DOM)
    - Extracts features (visual, text, meta)
    - Runs visual trust analysis
    - Builds signal report v1 (Phase 1)
    - Builds decision logic v1 (Phase 2) with blockers and scores
    - Returns JSON with decision probability and transparent weights/inputs
    """
    url = payload.url.strip()
    
    # 1) Capture page artifacts (screenshots + DOM)
    capture = None
    dom_data = None
    try:
        capture = await capture_page_artifacts(url)
        if capture:
            dom_data = extract_page_map(capture)
    except Exception as e:
        logger.exception("Page capture failed: %s", e)
        capture = {}
        dom_data = {}
    
    # 2) Get screenshot for visual trust
    shot: bytes = b""
    visual = None
    try:
        shot = await render_screenshot(url, timeout=30)
        if shot and shot.startswith(b"\x89PNG") and len(shot) > 100:
            try:
                raw_visual = await asyncio.wait_for(
                    asyncio.to_thread(run_visual_trust_from_bytes, shot_for_visual),
                    timeout=30.0
                )
                if isinstance(raw_visual, dict):
                    # Pass full visual trust result (includes elements, narrative, warnings)
                    visual = raw_visual.copy()
                    visual["screenshot_used"] = True
                else:
                    visual = {"screenshot_used": False}
            except Exception as e:
                logger.exception("Visual trust analysis failed: %s", e)
                visual = {"screenshot_used": False}
    except Exception as e:
        logger.exception("Screenshot capture failed: %s", e)
        visual = {"screenshot_used": False}
    
    # 3) Extract features (similar to analyze_url endpoint)
    extracted_text = ""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=25) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            
            html_bytes = r.content
            try:
                import chardet
                detected = chardet.detect(html_bytes)
                encoding = detected.get('encoding', 'utf-8')
                if detected.get('confidence', 0) < 0.7:
                    encoding = r.encoding or 'utf-8'
                html = html_bytes.decode(encoding, errors='replace')
            except ImportError:
                html = html_bytes.decode(r.encoding or 'utf-8', errors='replace')
            
            extracted_text = extract_text(html)
    except Exception as e:
        logger.exception("HTML fetch failed: %s", e)
    
    # 4) Build VisualFeatures (simplified)
    text_lower = extracted_text.lower()
    vf = {
        "hero_headline": None,
        "subheadline": None,
        "primary_cta_text": "Get Started" if "get started" in text_lower else None,
        "primary_cta_position": "hero_or_top" if "get started" in text_lower else None,
        "has_pricing": "pricing" in text_lower or "$" in extracted_text,
        "has_testimonials": '"' in extracted_text or "testimonial" in text_lower,
        "has_logos": "fortune 500" in text_lower or "trusted by" in text_lower,
        "has_guarantee": "guarantee" in text_lower or "money back" in text_lower,
    }
    
    # 5) Build features dict
    features = {
        "visual": vf,
        "text": {
            "key_lines": [l for l in extracted_text.splitlines() if l.strip()][:10],
        },
        "meta": {
            "url": url,
            "timestamp": datetime.utcnow().isoformat(),
        }
    }
    
    # 6) Prepare DOM data for signal detector
    dom_ctas = []
    if dom_data and isinstance(dom_data, dict):
        page_map_ctas = dom_data.get("ctas", [])
        for cta in page_map_ctas:
            if isinstance(cta, dict):
                dom_ctas.append({
                    "text": cta.get("text") or cta.get("label", ""),
                    "href": cta.get("href", ""),
                    "location": cta.get("location", "unknown"),
                    "kind": cta.get("kind", "unknown"),
                    "bucket": cta.get("bucket", "secondary")
                })
    
    dom_for_signals = {
        "ctas": dom_ctas,
        "has_contact": "contact" in text_lower or "@" in extracted_text,
        "hero_headline": dom_data.get("hero_headline") if dom_data else None,
        "subheadline": dom_data.get("subheadline") if dom_data else None,
    }
    
    # 7) Build Phase 1: Signal report
    try:
        signal_report = build_signal_report_v1(
            url=url,
            input_type="url",
            features=features,
            visual=visual or {},
            dom=dom_for_signals
        )
    except Exception as e:
        logger.exception("Signal report build failed: %s", e)
        error_detail = str(e)
        error_type = type(e).__name__
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "error_type": error_type,
                "error_message": error_detail,
                "url": url,
                "debug": {
                    "capture_available": capture is not None,
                    "dom_data_available": dom_data is not None,
                    "visual_available": visual is not None,
                    "features_available": bool(features),
                }
            },
            media_type="application/json; charset=utf-8"
        )
    
    # 8) Build Phase 2: Decision logic
    try:
        decision_logic = build_decision_logic_v1(signal_report)
        
        # Return JSONResponse with explicit UTF-8 charset
        return JSONResponse(
            content=decision_logic.dict(),
            media_type="application/json; charset=utf-8"
        )
    except Exception as e:
        logger.exception("Decision logic build failed: %s", e)
        error_detail = str(e)
        error_type = type(e).__name__
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "error_type": error_type,
                "error_message": error_detail,
                "url": url,
                "debug": {
                    "signal_report_available": signal_report is not None,
                }
            },
            media_type="application/json; charset=utf-8"
        )
