from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class EvidenceItem(BaseModel):
    source: str = Field(..., description="text|visual|dom")
    detail: str


class CTAItem(BaseModel):
    text: str
    href: Optional[str] = None
    kind: str = Field(..., description="button|link|form_submit|unknown")
    is_primary_candidate: bool = False
    has_action_verb: bool = False
    has_outcome_language: bool = False
    location: str = Field(..., description="above_fold|below_fold|unknown")
    bucket: str = Field(..., description="nav|action|content|footer")


class SignalReportV1(BaseModel):
    url: str
    input_type: str = Field(..., description="url|html")
    screenshot_used: bool = False

    # CTA signals
    cta_detected: bool = False
    primary_cta_detected: bool = False
    cta_count_total: int = Field(0, description="Total count of all CTAs (all buckets combined)")
    cta_count_action: int = 0
    cta_count_nav: int = 0
    cta_count_content: int = 0
    cta_count_above_fold: Optional[int] = None
    above_fold_available: bool = False
    ctas: List[CTAItem] = []

    # Trust signals
    has_testimonials: bool = False
    has_logos: bool = False
    has_pricing: bool = False
    has_guarantee: bool = False
    has_contact: bool = False

    # Clarity signals
    hero_headline: Optional[str] = None
    subheadline: Optional[str] = None

    # Risk signals
    risk_flags: List[str] = []

    # Raw evidence for debugging/traceability
    evidence: List[EvidenceItem] = []
    raw: Dict[str, Any] = {}
    
    # Debug fingerprint to verify code is loaded
    debug_build: str = "signals_v1_build_20251221_0939"

