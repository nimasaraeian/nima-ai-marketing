from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any, Dict, List, Literal, Optional

from api.vision.local_visual_extractor import extract_visual_elements
from api.cognitive_friction_engine import (
    VisualElement,
    VisualTrustResult,
    VISUAL_TRUST_SYSTEM_PROMPT,
    get_client,
)

logger = logging.getLogger("image_trust_service")


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _label_from_score(score: float) -> Literal["Low", "Medium", "High"]:
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def _py(v: Any) -> Any:
    """Convert numpy scalars and other non-serializable values to plain Python."""
    try:  # pragma: no cover - defensive
        import numpy as np  # type: ignore[import-not-found]

        if isinstance(v, np.floating):
            return float(v)
        if isinstance(v, np.integer):
            return int(v)
    except Exception:  # noqa: BLE001
        pass
    return v


def _sanitize_analysis(a: dict | None) -> dict:
    if not isinstance(a, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in a.items():
        out[str(k)] = _py(v)
    return out


def _sanitize_role(role: str | None) -> str:
    # اگر مدل roleها رو سخت‌گیرانه گرفته، اینجا امنش می‌کنیم
    r = (role or "other").strip()
    return r


def _build_local_visual_result(
    file_bytes: bytes,
    extracted: Dict | None = None,
    debug: bool = False,
) -> VisualTrustResult:
    if extracted is None:
        extracted = extract_visual_elements(file_bytes, debug=debug)

    elements_raw = extracted.get("elements", []) or []
    metrics = extracted.get("metrics", {}) or {}
    analysis_status = extracted.get("analysisStatus")
    error_message = extracted.get("error")

    elements: List[VisualElement] = []
    for e in elements_raw:
        try:
            elements.append(
                VisualElement(
                    id=str(e.get("id") or f"element_{len(elements)}"),
                    role=_sanitize_role(e.get("role")),
                    approx_position=str(e.get("approx_position") or "middle-center"),
                    text=e.get("text"),
                    visual_cues=[str(x) for x in (e.get("visual_cues") or [])],
                    analysis=_sanitize_analysis(e.get("analysis") or {}),
                )
            )
        except Exception as exc:  # noqa: BLE001
            # Skip invalid elements - return only real extracted elements
            logger.warning(
                "VisualElement validation failed, skipping element. err=%s raw=%s",
                exc,
                e,
            )
            continue

    edge_density = float(metrics.get("edge_density", 0.0))
    text_block_density = float(metrics.get("text_block_density", 0.0))
    has_cta = any(el.role and "cta" in el.role for el in elements)
    has_social = any(el.role == "logos" for el in elements)
    has_headline = any(el.role == "headline" for el in elements)

    score = 50.0
    if has_cta:
        score += 10
    if has_social:
        score += 10
    if has_headline:
        score += 5
    if edge_density > 0.12:
        score -= 15
    elif edge_density < 0.04:
        score += 5
    if text_block_density > 0.12:
        score -= 8

    score = _clamp(score)
    label = _label_from_score(score)

    warnings: List[str] = []
    if elements and len(elements) < 3:
        warnings.append("partial_elements")

    # Check for insufficient UI understanding
    if analysis_status == "fallback" and error_message == "vision_model_insufficient_ui_understanding":
        status: Literal["ok", "fallback"] = "fallback"
        notes = "vision_model_insufficient_ui_understanding"
    elif not elements:
        raise ValueError("Local extractor returned no elements.")
    else:
        status = "ok"
        notes = None
        if warnings:
            notes = f"Partial extraction (elements={len(elements)})."

    narrative: List[str] = []
    if has_cta:
        narrative.append("Found CTA-like button candidates.")
    else:
        narrative.append("CTA not detected; ensure a clear primary action.")
    if has_social:
        narrative.append("Detected possible social proof/logo strip.")
    else:
        narrative.append("No obvious social proof detected.")
    if edge_density > 0.12:
        narrative.append("Layout appears cluttered (high edge density).")
    if text_block_density > 0.12:
        narrative.append("Dense text regions detected; consider simplifying.")
    if has_headline:
        narrative.append("Prominent headline region detected.")

    return VisualTrustResult(
        status=status,
        label=label,
        overall_score=score,
        distribution=None,
        notes=notes,
        warnings=warnings,
        elements=elements,
        narrative=narrative,
    )


def _run_openai_fallback(file_bytes: bytes, content_type: str) -> VisualTrustResult:
    image_b64 = base64.b64encode(file_bytes).decode("utf-8")
    data_url = f"data:{content_type or 'image/png'};base64,{image_b64}"

    client = get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": VISUAL_TRUST_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze this landing page screenshot. Return JSON with elements, narrative, overall_visual_trust {label, score}.",
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        temperature=0.2,
        max_tokens=2000,
    )

    raw_content = response.choices[0].message.content or ""
    raw_json = raw_content
    if "```json" in raw_json:
        raw_json = raw_json.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_json:
        raw_json = raw_json.split("```")[1].split("```")[0].strip()

    data = json.loads(raw_json)
    raw_elements = data.get("elements", []) or []
    elements: List[VisualElement] = []
    for e in raw_elements:
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
        except Exception as exc:
            logger.warning("OpenAI fallback element parse failed: %s", exc)
            continue

    overall = data.get("overall_visual_trust") or {}
    score = float(overall.get("score", 50))
    label_raw = (overall.get("label") or "").lower()
    label: Optional[Literal["Low", "Medium", "High"]] = None
    if "low" in label_raw:
        label = "Low"
    elif "medium" in label_raw:
        label = "Medium"
    elif "high" in label_raw:
        label = "High"
    else:
        label = _label_from_score(score)

    # No fallback - return error if no elements found
    if not elements:
        raise ValueError("OpenAI fallback returned no elements.")
    
    return VisualTrustResult(
        status="ok",
        label=label,
        overall_score=_clamp(score),
        distribution=None,
        notes=None,
        warnings=[],
        elements=elements,
        narrative=data.get("narrative") or [],
    )


def analyze_image_trust_bytes(image_bytes: bytes, debug: bool = False) -> Dict[str, Any]:
    """
    Core image trust analysis logic.
    Used by both /api/analyze/image-trust and /analyze-url.
    
    Never returns fallback status. Raises exceptions on failure which should be
    caught by callers and converted to error format.
    """
    if not image_bytes:
        raise ValueError("Empty image bytes")

    max_size = 10 * 1024 * 1024
    if len(image_bytes) > max_size:
        raise ValueError(f"File too large. Maximum size is {max_size // (1024*1024)}MB")

    # OpenAI Vision fallback disabled - using local extractor only
    use_openai_fallback = False  # Hardcoded to False - local extractor only
    content_type = "image/png"

    try:
        extracted = extract_visual_elements(image_bytes, debug=debug)
        local_result = _build_local_visual_result(image_bytes, extracted=extracted, debug=debug)
        result_dict = local_result.dict()
        debug_info = extracted.get("debug") if isinstance(extracted, dict) else None
        if debug_info:
            result_dict["debug"] = debug_info
        return result_dict
    except ValueError as ve:
        # Check if it's an unpack error
        error_msg = str(ve)
        if "too many values to unpack" in error_msg or "expected 3" in error_msg or "not enough values to unpack" in error_msg:
            logger.error("Unpack error in visual extractor: %s", ve, exc_info=True)
            import traceback
            logger.error("Full traceback:\n%s", traceback.format_exc())
            # Try OpenAI fallback if enabled
            if use_openai_fallback:
                try:
                    oa_result = _run_openai_fallback(image_bytes, content_type)
                    oa_dict = oa_result.dict()
                    debug_info = extracted.get("debug") if isinstance(extracted, dict) and "extracted" in locals() else None
                    if debug_info:
                        oa_dict["debug"] = debug_info
                    return oa_dict
                except Exception as fallback_err:
                    logger.exception("OpenAI fallback also failed: %s", fallback_err)
                    raise ValueError(f"Unpack error in visual extractor and fallback failed: {error_msg}") from ve
            else:
                raise ValueError(f"Unpack error in visual extractor: {error_msg}") from ve
        
        # Local extractor failed - try OpenAI fallback if enabled
        if use_openai_fallback:
            try:
                oa_result = _run_openai_fallback(image_bytes, content_type)
                oa_dict = oa_result.dict()
                debug_info = extracted.get("debug") if isinstance(extracted, dict) and "extracted" in locals() else None
                if debug_info:
                    oa_dict["debug"] = debug_info
                return oa_dict
            except Exception as fallback_err:
                # Both local and OpenAI fallback failed - re-raise the original error
                logger.exception("OpenAI fallback also failed: %s", fallback_err)
                raise ve
        else:
            # No fallback enabled - re-raise
            raise

