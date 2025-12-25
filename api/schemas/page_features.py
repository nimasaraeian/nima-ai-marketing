from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


FEATURES_SCHEMA_VERSION = "1.0"


class VisualFeatures(BaseModel):
    hero_headline: Optional[str] = None
    subheadline: Optional[str] = None
    primary_cta_text: Optional[str] = None
    primary_cta_position: Optional[str] = None
    has_pricing: Optional[bool] = None
    has_testimonials: Optional[bool] = None
    has_logos: Optional[bool] = None
    has_guarantee: Optional[bool] = None
    has_faq: Optional[bool] = None
    has_security_badges: Optional[bool] = None
    visual_clutter_level: Optional[float] = Field(
        default=None, description="0..1 where higher = more clutter"
    )
    cta_contrast_level: Optional[float] = Field(
        default=None, description="0..1 where higher = better contrast"
    )
    info_hierarchy_quality: Optional[float] = Field(
        default=None, description="0..1 where higher = clearer hierarchy"
    )
    secondary_cta_text: Optional[str] = None
    secondary_cta_position: Optional[str] = None
    hero_media_type: Optional[str] = None  # image/video/none
    color_palette_comment: Optional[str] = None
    layout_style: Optional[str] = None  # single-column, two-column, etc.
    noted_elements: Optional[List[str]] = None  # raw cues extracted


class TextFeatures(BaseModel):
    key_lines: List[str] = []
    offers: List[str] = []
    claims: List[str] = []
    risk_reversal: List[str] = []
    audience_clarity: Optional[str] = None
    cta_copy: Optional[str] = None
    pricing_mentions: List[str] = []
    proof_points: List[str] = []
    differentiators: List[str] = []


class MetaFeatures(BaseModel):
    url: Optional[str] = None
    timestamp: Optional[str] = None
    screenshot_bytes: Optional[int] = None


class PageFeatures(BaseModel):
    featuresSchemaVersion: str = FEATURES_SCHEMA_VERSION
    visual: VisualFeatures
    text: TextFeatures
    meta: MetaFeatures

    class Config:
        extra = "allow"






















