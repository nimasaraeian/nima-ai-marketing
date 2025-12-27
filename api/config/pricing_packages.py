"""
Decision Brain Pricing & Packaging Configuration

This module defines the 3-tier packaging structure for Decision Brain services.
Pricing logic is configurable but follows value-based framing principles.

CORE RULES:
- Sell diagnosis, not execution
- No subscription pressure at start
- No "AI tool" framing
- No feature lists
- Position as strategic diagnostic engagement
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class PricingTier(str, Enum):
    """Pricing tier identifiers"""
    DIAGNOSIS = "diagnosis"
    DEEP_DIVE = "deep_dive"
    PARTNERSHIP = "partnership"


@dataclass
class PackageFeature:
    """Individual feature/item included in a package"""
    title: str
    description: str


@dataclass
class PricingPackage:
    """Complete pricing package definition"""
    tier: PricingTier
    name: str
    positioning_line: str
    features: List[PackageFeature]
    pricing_note: str  # Value framing, not hardcoded price
    cta_text: str = "Start with Decision Diagnosis"
    cta_route: str = "/decision-diagnosis"


# ====================================================
# TIER 1 — Decision Diagnosis (Entry / Core)
# ====================================================

TIER_1_DIAGNOSIS = PricingPackage(
    tier=PricingTier.DIAGNOSIS,
    name="Decision Diagnosis",
    positioning_line="Identify why users hesitate — before spending on redesign or ads.",
    features=[
        PackageFeature(
            title="Full Decision Brain Analysis",
            description="One page or one flow analyzed with context-aware outcome detection"
        ),
        PackageFeature(
            title="Confidence Scoring",
            description="Understand how certain we are about the diagnosis"
        ),
        PackageFeature(
            title="Client-Ready Decision Report",
            description="Professional 7-section report you can send directly to stakeholders"
        ),
        PackageFeature(
            title="Clear 'What to Fix First' Logic",
            description="Priority intervention that addresses the core psychological barrier"
        ),
    ],
    pricing_note=(
        "Priced to filter unserious clients while remaining accessible as entry to larger projects. "
        "One wrong decision can cost more than this diagnosis."
    ),
    cta_text="Start with Decision Diagnosis",
    cta_route="/decision-diagnosis"
)


# ====================================================
# TIER 2 — Decision Deep Dive (High-Value Project)
# ====================================================

TIER_2_DEEP_DIVE = PricingPackage(
    tier=PricingTier.DEEP_DIVE,
    name="Decision Deep Dive",
    positioning_line="Understand how decisions break across the entire user journey.",
    features=[
        PackageFeature(
            title="Multi-Page or Journey-Level Analysis",
            description="Analysis across multiple touchpoints in the user journey"
        ),
        PackageFeature(
            title="Cross-Context Outcome Comparison",
            description="See how decision failures differ across pages or flows"
        ),
        PackageFeature(
            title="Secondary Outcome Modeling",
            description="Understand compound blockers and their interactions"
        ),
        PackageFeature(
            title="Strategic Decision Map",
            description="Visual map of where decisions break and why"
        ),
        PackageFeature(
            title="Priority Roadmap",
            description="What to change now vs. later, with strategic sequencing"
        ),
    ],
    pricing_note=(
        "Project-based pricing for comprehensive journey analysis. "
        "Value anchored to cost of wrong decisions across multiple touchpoints."
    ),
    cta_text="Start with Decision Diagnosis",
    cta_route="/decision-diagnosis"
)


# ====================================================
# TIER 3 — Decision Partnership (Advisory)
# ====================================================

TIER_3_PARTNERSHIP = PricingPackage(
    tier=PricingTier.PARTNERSHIP,
    name="Decision Strategy Partnership",
    positioning_line="A strategic partner focused on how users decide — not just how pages look.",
    features=[
        PackageFeature(
            title="Ongoing Decision Analysis",
            description="Continuous diagnostics as you iterate and launch"
        ),
        PackageFeature(
            title="Iterative Diagnostics",
            description="Track how decision patterns change with each update"
        ),
        PackageFeature(
            title="Support Across Launches",
            description="Decision analysis for new products, pricing, or positioning changes"
        ),
        PackageFeature(
            title="Strategic Decision Advisory",
            description="Guidance on decision architecture, not just page optimization"
        ),
    ],
    pricing_note=(
        "Advisory engagement for teams who want decision intelligence as a strategic capability. "
        "Pricing reflects ongoing strategic value, not per-page analysis."
    ),
    cta_text="Start with Decision Diagnosis",
    cta_route="/decision-diagnosis"
)


# ====================================================
# PACKAGE REGISTRY
# ====================================================

ALL_PACKAGES: Dict[PricingTier, PricingPackage] = {
    PricingTier.DIAGNOSIS: TIER_1_DIAGNOSIS,
    PricingTier.DEEP_DIVE: TIER_2_DEEP_DIVE,
    PricingTier.PARTNERSHIP: TIER_3_PARTNERSHIP,
}


def get_package(tier: PricingTier) -> PricingPackage:
    """Get package by tier"""
    return ALL_PACKAGES[tier]


def get_all_packages() -> List[PricingPackage]:
    """Get all packages in tier order"""
    return [
        TIER_1_DIAGNOSIS,
        TIER_2_DEEP_DIVE,
        TIER_3_PARTNERSHIP,
    ]


def get_package_by_name(name: str) -> Optional[PricingPackage]:
    """Get package by name (case-insensitive)"""
    name_lower = name.lower()
    for package in ALL_PACKAGES.values():
        if package.name.lower() == name_lower:
            return package
    return None





























