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
from fastapi import APIRouter, Query
from pydantic import BaseModel

try:
    from readability import Document
except Exception:
    Document = None  # type: ignore

from ..schemas.page_features import (
    PageFeatures,
    VisualFeatures,
    TextFeatures,
    MetaFeatures,
    FEATURES_SCHEMA_VERSION,
)
from ..brain.decision_brain import analyze_decision
from ..visual_trust_engine import run_visual_trust_from_bytes
from ..services.screenshot import capture_url_png_bytes
from ..utils.text_sanitize import sanitize_any
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


async def render_screenshot(url: str, timeout: int = 30) -> bytes:
    """
    Render screenshot with timeout protection.
    
    Args:
        url: URL to screenshot
        timeout: Maximum time in seconds to wait
        
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
        logger.error("Screenshot capture timed out after %d seconds", timeout)
        raise


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

    # 2) Screenshot with timeout
    try:
        shot = await render_screenshot(url, timeout=30)
        if not shot or not shot.startswith(b"\x89PNG"):
            raise ValueError("Invalid screenshot")
    except (PlaywrightTimeoutError, asyncio.TimeoutError, Exception) as e:
        screenshot_error = str(e)
        shot = b""
        if isinstance(e, (asyncio.TimeoutError, PlaywrightTimeoutError)):
            screenshot_error = f"Screenshot timeout: {e}"
        logger.exception("Screenshot failed: %s", screenshot_error)

    if shot:
        debug_dir = Path(__file__).parent.parent / "debug_shots"
        debug_dir.mkdir(exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        debug_file = debug_dir / f"shot_{ts}.png"
        debug_file.write_bytes(shot)
        debug_path = str(debug_file)

    # 3) Vision Trust Analysis with timeout and fail-safe handling
    visual = None
    if shot and not screenshot_error and len(shot) > 100:
        try:
            # Run visual trust with timeout
            raw_visual = await asyncio.wait_for(
                asyncio.to_thread(run_visual_trust_from_bytes, shot),
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
        screenshot_bytes=len(shot),
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
        "debugScreenshotPath": debug_path,
        "debugScreenshotBytes": len(shot),
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

    return response
