"""
OpenAI Vision provider (isolated here).
Returns normalized vision output; no brain/business logic.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Try to find .env file in project root
project_root = Path(__file__).parent.parent.parent.parent
env_file = project_root / ".env"

# Load .env file if it exists
if env_file.exists():
    load_dotenv(env_file, override=True)
else:
    load_dotenv()


def _client():
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


def analyze_image(image_bytes: bytes, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Call OpenAI vision and return normalized schema.
    """
    try:
        import base64

        b64 = base64.b64encode(image_bytes).decode("ascii")
        client = _client()
        resp = client.chat.completions.create(
            model=model or os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "Return ONLY JSON with label, confidence, probs."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Classify trust level of this landing page (low/medium/high)."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "auto"}},
                    ],
                },
            ],
            temperature=0,
        )
        content = resp.choices[0].message.content or ""
        import json

        try:
            data = json.loads(content)
            label = data.get("label")
            probs = data.get("probs")
            confidence = data.get("confidence")
        except Exception:
            label = None
            probs = None
            confidence = None

        return {
            "analysisStatus": "ok" if label else "unavailable",
            "label": label,
            "confidence": confidence,
            "probs": probs,
            "error": None if label else "OpenAI returned invalid JSON",
        }
    except Exception as e:  # noqa: BLE001
        return {
            "analysisStatus": "unavailable",
            "label": None,
            "confidence": None,
            "probs": None,
            "error": f"OpenAI vision failed: {type(e).__name__}: {e}",
        }


