"""
CRITICAL ARCHITECTURE BOUNDARY:
- Vision analysis is isolated behind this adapter.
- Brain/Decision logic must NEVER import or call providers directly.
- All OpenAI usage stays inside provider modules only.
"""
from __future__ import annotations

import os
from typing import Any, Dict

from ..services.image_trust_service import analyze_image_trust_bytes


def _normalize(result: Dict[str, Any], error: str | None = None) -> Dict[str, Any]:
    """
    Normalize provider output to the canonical schema.
    """
    return {
        "analysisStatus": result.get("analysisStatus"),
        "label": result.get("label"),
        "confidence": result.get("confidence"),
        "probs": result.get("probs"),
        "error": result.get("error") or error,
    }


def analyze_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Entry point for all vision providers.
    Respects ENV flags and returns a normalized result.
    """
    enabled = os.getenv("VISION_ENABLED", "true").lower() != "false"
    if not enabled:
        return {
            "analysisStatus": "unavailable",
            "label": None,
            "confidence": None,
            "probs": None,
            "error": "Vision disabled by VISION_ENABLED=false",
        }

    provider = os.getenv("VISION_PROVIDER", "openai").lower()
    model = os.getenv("VISION_MODEL", "")

    if provider == "local":
        # Use OpenCV + local extractor (no TensorFlow)
        res = analyze_image_trust_bytes(image_bytes)
        # Normalize to match expected schema
        normalized = {
            "analysisStatus": res.get("status", "ok"),
            "label": res.get("label"),
            "confidence": res.get("overall_score", 0.0) / 100.0 if res.get("overall_score") else None,
            "probs": res.get("distribution"),
            "error": res.get("error") or (None if res.get("status") == "ok" else "analysis_failed"),
        }
        return normalized

    if provider == "openai":
        try:
            from api.vision.providers.openai_vision import analyze_image as openai_analyze
        except Exception as e:  # noqa: BLE001
            return {
                "analysisStatus": "unavailable",
                "label": None,
                "confidence": None,
                "probs": None,
                "error": f"OpenAI provider not available: {e}",
            }
        res = openai_analyze(image_bytes, model=model or None)
        return _normalize(res)

    return {
        "analysisStatus": "unavailable",
        "label": None,
        "confidence": None,
        "probs": None,
        "error": f"Unknown vision provider: {provider}",
    }




