"""
Canonical PageMap schema for unified intake pipeline.

This schema normalizes URL, IMAGE, and TEXT inputs into a single contract
that the Decision Engine can consume.
"""
from typing import Literal, Optional, List
from pydantic import BaseModel, Field


class PrimaryCTA(BaseModel):
    """Primary call-to-action information."""
    text: Optional[str] = Field(default=None, description="CTA button/link text")
    intent: Optional[str] = Field(default=None, description="Intent (e.g., 'signup', 'purchase', 'contact')")
    clarity: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Clarity score 0-1")


class Offer(BaseModel):
    """Pricing/offer information."""
    type: Optional[str] = Field(default=None, description="Offer type (e.g., 'discount', 'trial', 'subscription')")
    value: Optional[str] = Field(default=None, description="Offer value (e.g., '50% off', 'Free trial')")
    price_info: Optional[str] = Field(default=None, description="Price information text")


class VisualHierarchy(BaseModel):
    """Visual hierarchy and layout information."""
    focus: Optional[str] = Field(default=None, description="Main visual focus element")
    cta_visibility: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="CTA visibility score 0-1")
    noise: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Visual noise/clutter score 0-1")


class PageMap(BaseModel):
    """
    Canonical page structure map.
    
    This is the normalized contract that all extractors (URL, IMAGE, TEXT)
    must produce and that the Decision Engine consumes.
    """
    source: Literal["url", "image", "text"] = Field(..., description="Source of the page data")
    goal: str = Field(default="leads", description="Analysis goal (leads, sales, booking, etc.)")
    
    # Core content
    page_type: Optional[str] = Field(default=None, description="Detected page type")
    headline: Optional[str] = Field(default=None, description="Main headline (H1)")
    subheadline: Optional[str] = Field(default=None, description="Subheadline (H2 or hero subtitle)")
    
    # CTAs
    primary_cta: Optional[PrimaryCTA] = Field(default=None, description="Primary CTA information")
    secondary_ctas: List[dict] = Field(default_factory=list, description="Secondary CTAs as dicts")
    
    # Offer/Pricing
    offer: Optional[Offer] = Field(default=None, description="Pricing/offer information")
    
    # Signals
    trust_signals: List[str] = Field(default_factory=list, description="Trust signal keywords/texts")
    risk_signals: List[str] = Field(default_factory=list, description="Risk signal keywords/texts")
    friction_signals: List[str] = Field(default_factory=list, description="Friction signal keywords/texts")
    
    # Visual
    visual_hierarchy: Optional[VisualHierarchy] = Field(default=None, description="Visual hierarchy information")
    
    # Copy
    copy_snippets: List[str] = Field(default_factory=list, description="Key copy snippets from the page")
    
    # Metadata
    language: Optional[str] = Field(default="en", description="Detected language")
    
    class Config:
        extra = "allow"  # Allow additional fields for flexibility

