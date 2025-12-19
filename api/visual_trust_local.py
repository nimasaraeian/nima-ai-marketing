"""
DEPRECATED: This file is kept for backward compatibility but no longer uses TensorFlow.
All functionality has been moved to api/services/image_trust_service.py which uses OpenCV + local extractor.
"""
from __future__ import annotations

from typing import Any, Dict

from .services.image_trust_service import analyze_image_trust_bytes


def analyze_visual_trust_local(image_bytes: bytes) -> Dict[str, Any]:
    """
    DEPRECATED: Use analyze_image_trust_bytes from api.services.image_trust_service instead.
    
    This function is kept for backward compatibility but now delegates to the OpenCV-based implementation.
    """
    result = analyze_image_trust_bytes(image_bytes)
    
    # Convert to old format for backward compatibility
    return {
        "analysisStatus": result.get("status", "ok"),
        "label": result.get("label"),
        "confidence": result.get("overall_score", 0.0) / 100.0 if result.get("overall_score") else None,
        "probs": result.get("distribution"),
        "error": result.get("error") or (None if result.get("status") == "ok" else "analysis_failed"),
    }
