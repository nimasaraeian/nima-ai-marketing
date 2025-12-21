"""
DEPRECATED: This file is kept for backward compatibility but no longer uses TensorFlow.
All functionality has been moved to api/services/image_trust_service.py which uses OpenCV + local extractor.
"""
from __future__ import annotations

from typing import Dict


def get_model_status() -> str:
    """
    DEPRECATED: TensorFlow model loading removed.
    Returns status message indicating OpenCV-based implementation is used.
    """
    return "VisualTrust: Using OpenCV + local extractor (TensorFlow removed)"


def predict_visual_trust(image_bytes: bytes) -> Dict:
    """
    DEPRECATED: Use analyze_image_trust_bytes from api.services.image_trust_service instead.
    
    This function is kept for backward compatibility but now returns unavailable status.
    """
    return {
        "analysisStatus": "unavailable",
        "label": None,
        "confidence": None,
        "probs": None,
        "error": "TensorFlow model removed. Use analyze_image_trust_bytes from api.services.image_trust_service instead.",
    }
