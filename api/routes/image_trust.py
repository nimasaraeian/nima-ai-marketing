"""
Image Trust Analysis API Route
==============================

Endpoint for analyzing visual trust level of uploaded images.

This version is stabilized:
- The main endpoint POST /api/analyze/image-trust delegates to the local visual trust pipeline
  (same as /api/analyze/image-trust-local) to avoid legacy/unstable paths.
- Keeps response contract: {"success": bool, "analysis": {...}}
- Normalizes label to "Low" | "Medium" | "High"
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Dict, Literal, Optional, List

from fastapi import APIRouter, File, HTTPException, UploadFile, Query

# Use OpenCV + local extractor (no TensorFlow dependency)
from api.services.image_trust_service import analyze_image_trust_bytes

# Optional: OpenAI Vision endpoint (kept, but isolated)
from api.cognitive_friction_engine import (
    VisualTrustResult,
    VisualElement,
    VISUAL_TRUST_SYSTEM_PROMPT,
    get_client,
)

try:
    import cv2
except Exception:
    cv2 = None  # health endpoint will handle this gracefully


logger = logging.getLogger("image_trust")

Label = Literal["Low", "Medium", "High"]


def _normalize_label(label: Optional[str]) -> Optional[Label]:
    if not label:
        return None
    s = str(label).strip().lower()
    if s == "low":
        return "Low"
    if s == "medium":
        return "Medium"
    if s == "high":
        return "High"
    # if unknown, leave None (or choose a default)
    return None


# Router (NOTE: prefix is typically applied in app.py via include_router)
router = APIRouter()


@router.get("/")
async def image_trust_root():
    """Root endpoint for image trust service."""
    return {
        "service": "image-trust",
        "status": "active",
        "endpoints": {
            "health": "/api/analyze/image-trust/health",
            "analyze": "/api/analyze/image-trust",
            "vision": "/api/analyze/image-trust/vision",
        },
        "engine": "opencv-local-extractor",
    }


@router.get("/health")
async def image_trust_health():
    """Health check endpoint."""
    return {
        "status": "active",
        "engine": "opencv-local-extractor",
        "opencv": (cv2.__version__ if cv2 is not None else "not_available"),
    }


@router.post("")
@router.post("/")
async def analyze_image(
    file: UploadFile = File(...),
    debug: bool = Query(False, description="(Reserved) kept for compatibility."),
) -> Dict[str, Any]:
    """
    Main endpoint used by UI and /analyze-url pipeline.

    IMPORTANT:
    This endpoint now uses the stable local pipeline (analyze_visual_trust_local)
    to avoid legacy unpack/model-output errors.
    """
    logger.info(
        "Image trust request received: filename=%s content_type=%s",
        file.filename,
        file.content_type,
    )

    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Empty file provided. Please upload a valid image file.")

        # Use OpenCV + local extractor (no TensorFlow)
        analysis = analyze_image_trust_bytes(file_bytes, debug=debug)

        # Normalize label casing if present
        if isinstance(analysis, dict) and "label" in analysis:
            analysis["label"] = _normalize_label(analysis.get("label")) or analysis.get("label")

        return {"success": True, "analysis": analysis}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Image trust analysis failed: %s", e)
        return {
            "success": False,
            "analysis": {
                "status": "error",
                "errorType": type(e).__name__,
                "errorMessage": str(e),
                "label": None,
                "overall_score": None,
                "distribution": None,
                "notes": None,
                "warnings": [],
                "elements": [],
                "narrative": [],
            },
        }


@router.post("/vision")
@router.post("/vision/")
async def analyze_image_trust_vision(file: UploadFile = File(...)) -> VisualTrustResult:
    """
    Optional: OpenAI Vision API analysis (kept as separate endpoint).
    Does NOT affect the stability of /api/analyze/image-trust.
    """
    try:
        logger.info(
            "Vision API image trust request received: filename=%s content_type=%s",
            file.filename,
            file.content_type,
        )

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file provided. Please upload a valid image file.")

        mime_type = file.content_type or "image/png"
        if not mime_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image (jpg, png, etc.)")

        image_b64 = base64.b64encode(content).decode("utf-8")
        data_url = f"data:{mime_type};base64,{image_b64}"

        client = get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": VISUAL_TRUST_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this landing page screenshot. Return JSON only."},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            temperature=0.2,
            max_tokens=2000,
        )

        raw_json = response.choices[0].message.content or ""

        # Extract JSON (handle markdown code blocks if present)
        if "```json" in raw_json:
            raw_json = raw_json.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_json:
            raw_json = raw_json.split("```")[1].split("```")[0].strip()

        data = json.loads(raw_json)

        elements: List[VisualElement] = []
        for e in data.get("elements", []):
            try:
                elements.append(
                    VisualElement(
                        id=e.get("id", f"element_{len(elements)}"),
                        role=e.get("role", "other"),
                        approx_position=e.get("approx_position", "middle-center"),
                        text=e.get("text"),
                        visual_cues=e.get("visual_cues") or [],
                        analysis=e.get("analysis") or {},
                    )
                )
            except Exception:
                continue

        overall = data.get("overall_visual_trust") or {}
        label = _normalize_label(overall.get("label"))
        score = overall.get("score")
        overall_score = float(score) if score is not None else None

        return VisualTrustResult(
            status="ok",
            label=label,
            overall_score=overall_score,
            distribution=None,
            notes=None,
            warnings=[],
            elements=elements,
            narrative=data.get("narrative") or [],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Vision API visual trust analysis failed: %s", e)
        return VisualTrustResult(
            status="fallback",
            notes=f"Vision API analysis failed: {str(e)}",
            warnings=[],
            elements=[],
            narrative=[],
        )
