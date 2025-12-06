"""
Schema definitions for landing friction dataset samples.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, ValidationError

Label = Literal["low", "medium", "high"]


class FrictionDimensions(BaseModel):
    """Numeric sub-scores for cognitive friction dimensions."""

    clarity: int = Field(..., ge=0, le=100)
    overload: int = Field(..., ge=0, le=100)
    trust: int = Field(..., ge=0, le=100)
    emotion: int = Field(..., ge=0, le=100)
    decision_flow: int = Field(..., ge=0, le=100)
    cta_strength: int = Field(..., ge=0, le=100)


class LandingFrictionSample(BaseModel):
    """Single labeled landing page sample."""

    id: str
    label: Label
    url: Optional[HttpUrl] = None
    content: str
    total_friction: int = Field(..., ge=0, le=100)
    dimensions: FrictionDimensions
    analysis: str
    quick_fixes: List[str]
    rewrite_examples: Dict[str, str] = Field(default_factory=dict)
    expected_result: Optional[Dict[str, Any]] = None


def load_sample(path: Path) -> Optional[LandingFrictionSample]:
    """
    Load and validate a single landing friction sample.
    Returns None if the file is invalid.
    """
    try:
        data = path.read_text(encoding="utf-8")
        return LandingFrictionSample.model_validate_json(data)
    except (OSError, ValidationError) as exc:
        return None







