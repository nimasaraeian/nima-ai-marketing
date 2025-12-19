"""
OpenAI Vision helper to extract structured visual features.
Returns only the JSON that matches VisualFeatures schema.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

from ..schemas.page_features import VisualFeatures

# Try to find .env file in project root
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"

# Load .env file if it exists
if env_file.exists():
    load_dotenv(env_file, override=True)
else:
    load_dotenv()

OPENAI_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")


def _get_openai_client():
    try:
        from openai import OpenAI
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"openai package missing: {e}")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Try reading directly from .env file
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8-sig') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and 'OPENAI_API_KEY' in line:
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip()
                                if key == 'OPENAI_API_KEY':
                                    # Remove quotes
                                    if value.startswith('"') and value.endswith('"'):
                                        value = value[1:-1]
                                    elif value.startswith("'") and value.endswith("'"):
                                        value = value[1:-1]
                                    api_key = value
                                    break
            except Exception:
                pass
    
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    return OpenAI(api_key=api_key)


SYSTEM_PROMPT = """
You are a structured vision extractor. Return ONLY valid JSON matching this schema:
{
  "hero_headline": str|null,
  "subheadline": str|null,
  "primary_cta_text": str|null,
  "primary_cta_position": str|null,
  "has_pricing": bool|null,
  "has_testimonials": bool|null,
  "has_logos": bool|null,
  "has_guarantee": bool|null,
  "has_faq": bool|null,
  "has_security_badges": bool|null,
  "visual_clutter_level": number|null,
  "cta_contrast_level": number|null,
  "info_hierarchy_quality": number|null,
  "secondary_cta_text": str|null,
  "secondary_cta_position": str|null,
  "hero_media_type": str|null,
  "color_palette_comment": str|null,
  "layout_style": str|null,
  "noted_elements": [str]|null
}
No commentary. No markdown. Only JSON.
"""


def _fallback_visual(error: str) -> Dict[str, Any]:
    return VisualFeatures(
        hero_headline=None,
        subheadline=None,
        primary_cta_text=None,
        primary_cta_position=None,
        has_pricing=None,
        has_testimonials=None,
        has_logos=None,
        has_guarantee=None,
        has_faq=None,
        has_security_badges=None,
        visual_clutter_level=None,
        cta_contrast_level=None,
        info_hierarchy_quality=None,
        secondary_cta_text=None,
        secondary_cta_position=None,
        hero_media_type=None,
        color_palette_comment=None,
        layout_style=None,
        noted_elements=[],
        # extra fields allowed by pydantic config
    ).dict() | {"_error": error}


def extract_features_from_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Call OpenAI Vision to extract visual features.
    Returns a dict that fits VisualFeatures. On failure, returns a minimal fallback.
    """
    try:
        client = _get_openai_client()
    except Exception as e:  # noqa: BLE001
        return _fallback_visual(f"OpenAI client unavailable: {e}")

    try:
        import base64

        b64 = base64.b64encode(image_bytes).decode("ascii")

        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.strip()},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract visual features. Return only JSON.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "auto"},
                        },
                    ],
                },
            ],
            temperature=0,
        )
        content = resp.choices[0].message.content
        if not content:
            return _fallback_visual("Empty OpenAI response")
        try:
            data = json.loads(content)
            return VisualFeatures(**data).dict()
        except Exception as e:  # noqa: BLE001
            return _fallback_visual(f"Invalid JSON from OpenAI: {e}")
    except Exception as e:  # noqa: BLE001
        return _fallback_visual(f"OpenAI vision failed: {type(e).__name__}: {e}")

