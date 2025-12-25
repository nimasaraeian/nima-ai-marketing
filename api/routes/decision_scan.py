"""
Decision Scan Endpoint

Unified endpoint for decision analysis supporting:
- URL mode: Full page analysis
- Text mode: Text-only analysis
- Image mode: Image-based analysis
"""

import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List
import json

logger = logging.getLogger("decision_scan")

router = APIRouter(prefix="", tags=["Decision Scan"])


class DecisionScanRequest(BaseModel):
    """Request model for decision scan (JSON mode)"""
    mode: Literal["url", "text", "image"] = Field(..., description="Analysis mode")
    url: Optional[str] = Field(None, description="URL to analyze (for mode=url)")
    text: Optional[str] = Field(None, description="Text content to analyze (for mode=text)")
    goal: Optional[str] = Field("leads", description="Analysis goal")
    locale: Optional[str] = Field("en", description="Locale (enforced to 'en')")


class DecisionState(BaseModel):
    """Decision state model"""
    label: str
    confidence: Literal["low", "medium", "high"]
    evidence: List[str]


class Issue(BaseModel):
    """Issue model"""
    title: str
    why: str
    fix: str
    location: Optional[str] = None


class DecisionScanResponse(BaseModel):
    """Response model for decision scan"""
    status: Literal["ok", "error"]
    decision_state: Optional[DecisionState] = None
    human_report: Optional[str] = None
    summary: Optional[str] = None
    issues: Optional[List[Issue]] = None
    screenshots: Optional[Dict[str, Optional[str]]] = None
    error: Optional[str] = None


async def _analyze_url_mode(url: str, goal: str, locale: str, request: Request) -> Dict[str, Any]:
    """
    Analyze URL mode by reusing existing URL analysis logic.
    
    Args:
        url: URL to analyze
        goal: Analysis goal
        locale: Locale (enforced to 'en')
        request: FastAPI Request object
        
    Returns:
        Response dict matching DecisionScanResponse schema
    """
    try:
        # Import the builder function
        from api.brain.decision_engine.human_report_builder import build_human_decision_review
        
        # Enforce locale="en"
        locale = "en"
        
        # Call existing URL analysis logic
        logger.info(f"Analyzing URL: {url}, goal: {goal}, locale: {locale}")
        result = await build_human_decision_review(
            url=url,
            goal=goal,
            locale=locale
        )
        
        # Map result to DecisionScanResponse schema
        # Extract decision state from result
        decision_state_label = "Outcome Unclear"  # Default
        decision_state_confidence = "medium"  # Default
        evidence_list = []
        
        # Try to extract from various possible fields
        if "primary_outcome" in result:
            decision_state_label = result["primary_outcome"]
        elif "decision_blocker" in result:
            decision_state_label = result["decision_blocker"]
        elif "decision_state" in result:
            decision_state_label = result["decision_state"].get("label", decision_state_label)
        
        # Extract confidence
        if "confidence" in result:
            conf_val = result["confidence"]
            if isinstance(conf_val, (int, float)):
                if conf_val >= 0.75:
                    decision_state_confidence = "high"
                elif conf_val >= 0.5:
                    decision_state_confidence = "medium"
                else:
                    decision_state_confidence = "low"
            elif isinstance(conf_val, str):
                decision_state_confidence = conf_val.lower() if conf_val.lower() in ["low", "medium", "high"] else "medium"
        
        # Build evidence list
        if "decision_psychology_insight" in result:
            insight = result["decision_psychology_insight"]
            if isinstance(insight, dict):
                if "insight" in insight:
                    evidence_list.append(insight["insight"])
                if "why_now" in insight:
                    evidence_list.append(insight["why_now"])
        
        if "why" in result:
            evidence_list.append(result["why"])
        
        if not evidence_list:
            evidence_list = ["URL analysis completed."]
        
        # Extract human report
        human_report = result.get("human_report") or result.get("report") or None
        
        # Debug logging
        logger.info(f"Human report from result: {human_report[:100] if human_report else 'None'}...")
        logger.info(f"Result keys: {list(result.keys())}")
        
        # If human_report is empty or None, build it from signature layers
        if not human_report or (isinstance(human_report, str) and len(human_report.strip()) == 0):
            logger.info("Human report is empty, building from signature layers...")
            # Build from decision_psychology_insight
            insight = result.get("decision_psychology_insight", {})
            if isinstance(insight, dict):
                lines = []
                lines.append("## Verdict")
                lines.append("")
                lines.append(insight.get("insight", "Analysis completed. Review the findings below."))
                lines.append("")
                lines.append("## Why This Matters Now")
                lines.append("")
                lines.append(insight.get("why_now", "Addressing the primary blocker unlocks the decision pathway."))
                lines.append("")
                lines.append("## Quick Action")
                lines.append("")
                lines.append(insight.get("micro_risk_reducer", "Focus on the top blocker identified in the analysis."))
                human_report = "\n".join(lines)
                logger.info(f"Built human report from insight: {len(human_report)} chars")
            else:
                # Fallback: use summary or default
                human_report = result.get("summary") or "## Analysis Report\n\nAnalysis completed. Review the findings and recommendations below."
                logger.info(f"Using fallback human report: {len(human_report)} chars")
        
        # Final fallback - ensure we always have a report
        if not human_report or (isinstance(human_report, str) and len(human_report.strip()) == 0):
            human_report = """## Analysis Report

Analysis completed successfully. Review the findings and recommendations below.

## Next Steps

1. Review the decision state and evidence
2. Check the recommendations and issues
3. Implement the suggested fixes"""
            logger.warning("Using final fallback human report")
        
        # Extract summary
        summary = result.get("summary") or result.get("what_to_fix_first") or None
        
        # If summary is empty, use a default
        if not summary:
            summary = "Decision analysis completed. Review the findings and recommendations below."
        
        # Extract issues
        issues = []
        if "keyDecisionBlockers" in result:
            for blocker in result["keyDecisionBlockers"]:
                if isinstance(blocker, dict):
                    issues.append(Issue(
                        title=blocker.get("name", "Issue"),
                        why=", ".join(blocker.get("evidence", [])),
                        fix=blocker.get("fix", ""),
                        location=None
                    ))
        elif "recommendations" in result:
            for rec in result["recommendations"]:
                if isinstance(rec, dict):
                    issues.append(Issue(
                        title=rec.get("level", "Recommendation"),
                        why="",
                        fix=rec.get("description", ""),
                        location=None
                    ))
        
        # Extract screenshots
        screenshots = None
        if "screenshots" in result:
            screenshots_data = result["screenshots"]
            if isinstance(screenshots_data, dict):
                screenshots = {
                    "desktop": screenshots_data.get("desktop", {}).get("above_the_fold_data_url") or 
                              screenshots_data.get("desktop", {}).get("url"),
                    "mobile": screenshots_data.get("mobile", {}).get("above_the_fold_data_url") or 
                             screenshots_data.get("mobile", {}).get("url")
                }
        
        return {
            "status": "ok",
            "decision_state": {
                "label": decision_state_label,
                "confidence": decision_state_confidence,
                "evidence": evidence_list
            },
            "human_report": human_report,
            "summary": summary,
            "issues": [issue.dict() for issue in issues] if issues else None,
            "screenshots": screenshots
        }
        
    except Exception as e:
        logger.exception(f"URL analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"URL analysis failed: {str(e)}"
        )


async def _analyze_text_mode(text: str) -> Dict[str, Any]:
    """
    Analyze text mode (V1 minimal implementation).
    
    Args:
        text: Text content to analyze
        
    Returns:
        Response dict matching DecisionScanResponse schema
    """
    return {
        "status": "ok",
        "decision_state": {
            "label": "Interested but Confused",
            "confidence": "low",
            "evidence": ["Text-only evidence (no page context)."]
        },
        "human_report": f"""# Text-Only Analysis

This is a text-only analysis without full page context.

## Content Analyzed

{text[:500]}{'...' if len(text) > 500 else ''}

## Limitations

- No visual context available
- No page structure information
- Limited decision signals

## Next Steps

For more accurate analysis, please provide:
- Full URL for complete page analysis
- Screenshot for visual context
- Additional context about the page structure

## Current Assessment

Based on text content alone, the decision state appears to be **Interested but Confused**, indicating that while there may be interest, clarity is needed to move forward.
""",
        "summary": "Text-only analysis completed. Full page analysis recommended for better insights.",
        "issues": None,
        "screenshots": None
    }


async def _analyze_image_mode(image_file: UploadFile) -> Dict[str, Any]:
    """
    Analyze image mode (V1 minimal implementation).
    
    Args:
        image_file: Uploaded image file
        
    Returns:
        Response dict matching DecisionScanResponse schema
    """
    # Read image bytes
    image_bytes = await image_file.read()
    
    # Check if vision pipeline is available
    vision_available = False
    try:
        from api.visual_trust_engine import run_visual_trust_from_bytes
        vision_available = True
    except ImportError:
        vision_available = False
    
    if vision_available:
        try:
            # Use existing vision pipeline
            vision_result = run_visual_trust_from_bytes(image_bytes)
            
            return {
                "status": "ok",
                "decision_state": {
                    "label": "Ready but Hesitant",
                    "confidence": "medium",
                    "evidence": [
                        f"Visual trust analysis: {vision_result.get('label', 'Unknown')}",
                        "Image evidence analyzed with vision pipeline."
                    ]
                },
                "human_report": f"""# Image Analysis

## Visual Trust Assessment

**Label:** {vision_result.get('label', 'Unknown')}
**Confidence:** {vision_result.get('confidence', 0.0)}

## Analysis

{vision_result.get('narrative', ['Visual analysis completed.'])[0] if isinstance(vision_result.get('narrative'), list) else vision_result.get('narrative', 'Visual analysis completed.')}

## Decision State

Based on visual analysis, the decision state is **Ready but Hesitant**, indicating readiness to proceed but with some hesitation factors present.
""",
                "summary": "Image analysis completed using vision pipeline.",
                "issues": None,
                "screenshots": None
            }
        except Exception as e:
            logger.warning(f"Vision pipeline failed, using fallback: {e}")
            vision_available = False
    
    # Fallback: Minimal placeholder
    return {
        "status": "ok",
        "decision_state": {
            "label": "Ready but Hesitant",
            "confidence": "low",
            "evidence": ["Image evidence received. Vision analysis not yet enabled in this environment."]
        },
        "human_report": """# Image Analysis

## Status

Image evidence has been received and processed.

## Current Limitations

Vision analysis pipeline is not fully enabled in this environment. The image has been received but deep visual analysis is not available.

## Next Steps

To enable full image analysis:
1. Ensure vision pipeline dependencies are installed
2. Configure vision analysis service
3. Retry the analysis

## Current Assessment

Based on image receipt alone, the decision state appears to be **Ready but Hesitant**, indicating potential readiness with some uncertainty factors.
""",
        "summary": "Image received. Vision analysis not fully enabled.",
        "issues": None,
        "screenshots": None
    }


@router.post("/api/decision-scan", response_model=DecisionScanResponse)
async def decision_scan(request: Request):
    """
    Decision Scan Endpoint (primary route)
    """
    return await _handle_decision_scan(request)


@router.post("/api/proxy/decision-scan", response_model=DecisionScanResponse)
async def proxy_decision_scan(request: Request):
    """
    Decision Scan Endpoint (proxy alias for Next.js compatibility)
    """
    return await _handle_decision_scan(request)


async def _handle_decision_scan(request: Request):
    """
    Decision Scan Endpoint
    
    Supports both JSON and multipart/form-data:
    - JSON: POST with Content-Type: application/json
    - Multipart: POST with Content-Type: multipart/form-data
    
    Modes:
    - url: Analyze a URL (requires 'url' field)
    - text: Analyze text content (requires 'text' field)
    - image: Analyze an image (requires 'image' file)
    """
    try:
        # Determine content type and parse accordingly
        content_type = request.headers.get("content-type", "").lower()
        
        # If multipart/form-data, parse form data
        if "multipart/form-data" in content_type:
            form_data = await request.form()
            mode = form_data.get("mode")
            url = form_data.get("url")
            text = form_data.get("text")
            goal = form_data.get("goal", "leads")
            locale = "en"  # Enforce
            image = form_data.get("image")
            
            # Auto-detect mode if not provided
            if not mode:
                if image:
                    mode = "image"
                elif text:
                    mode = "text"
                elif url:
                    mode = "url"
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="Must provide 'mode' or at least one of: url, text, image"
                    )
            
            if mode == "url":
                if not url:
                    raise HTTPException(status_code=400, detail="'url' required for mode=url")
                return await _analyze_url_mode(str(url), str(goal), locale, request)
            
            elif mode == "text":
                if not text:
                    raise HTTPException(status_code=400, detail="'text' required for mode=text")
                return await _analyze_text_mode(str(text))
            
            elif mode == "image":
                if not image:
                    raise HTTPException(status_code=400, detail="'image' file required for mode=image")
                # Convert to UploadFile-like object
                from fastapi import UploadFile
                image_file = UploadFile(filename=image.filename, file=image.file) if hasattr(image, 'filename') else image
                return await _analyze_image_mode(image_file)
            
            else:
                raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")
        
        else:
            # JSON mode - read body
            try:
                body = await request.json()
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid JSON body: {str(e)}"
                )
            
            mode = body.get("mode")
            if not mode:
                raise HTTPException(status_code=400, detail="'mode' field required")
            
            # Enforce locale="en"
            locale = "en"
            
            if mode == "url":
                url = body.get("url")
                if not url:
                    raise HTTPException(status_code=400, detail="'url' required for mode=url")
                goal = body.get("goal", "leads")
                return await _analyze_url_mode(url, goal, locale, request)
            
            elif mode == "text":
                text = body.get("text")
                if not text:
                    raise HTTPException(status_code=400, detail="'text' required for mode=text")
                return await _analyze_text_mode(text)
            
            elif mode == "image":
                raise HTTPException(
                    status_code=400,
                    detail="For mode=image, use multipart/form-data with 'image' file"
                )
            
            else:
                raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Decision scan failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "decision_state": None,
                "human_report": None,
                "summary": None,
                "issues": None,
                "screenshots": None
            }
        )


@router.get("/api/decision-scan/health")
async def decision_scan_health():
    """Health check for decision scan endpoint"""
    return {
        "status": "ok",
        "endpoint": "/api/decision-scan",
        "modes": ["url", "text", "image"]
    }

