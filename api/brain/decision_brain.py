"""
Deterministic “Decision Brain” scoring.
No OpenAI/LLM dependency; pure rule-based weighting.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from api.schemas.page_features import PageFeatures


@dataclass
class Blocker:
    name: str
    evidence: List[str]
    severity: str
    fix: str


def _bool_score(val, weight_true: float, weight_false: float) -> float:
    if val is True:
        return weight_true
    if val is False:
        return weight_false
    return 0.0


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def analyze_decision(features: PageFeatures) -> Dict:
    visual = features.visual
    text = features.text

    blockers: List[Blocker] = []

    trust = 50.0
    trust += _bool_score(visual.has_logos, 10, -5)
    trust += _bool_score(visual.has_testimonials, 12, -8)
    trust += _bool_score(visual.has_security_badges, 8, -6)
    trust += _bool_score(visual.has_guarantee, 6, -4)
    trust += _bool_score(visual.has_faq, 3, -2)

    friction = 50.0
    if visual.visual_clutter_level is not None:
        friction += (visual.visual_clutter_level - 0.5) * 40  # +/-20
    if visual.info_hierarchy_quality is not None:
        friction -= (visual.info_hierarchy_quality - 0.5) * 40  # clearer hierarchy reduces friction
    if visual.cta_contrast_level is not None:
        friction -= (visual.cta_contrast_level - 0.5) * 20
    friction += _bool_score(visual.has_pricing, -6, 6)

    clarity = 50.0
    if text.offers:
        clarity += 8
    else:
        clarity -= 8
    if text.audience_clarity:
        clarity += 6
    else:
        clarity -= 4
    if text.cta_copy:
        clarity += 4
    if text.proof_points:
        clarity += 6
    clarity -= _bool_score(visual.has_pricing, -2, 4)

    # Blockers
    if visual.has_pricing is False:
        blockers.append(Blocker("missing_pricing", ["Pricing not visible"], "high", "Show clear pricing or a CTA to pricing."))
    if visual.has_testimonials is False:
        blockers.append(Blocker("missing_testimonials", ["No testimonials/proof"], "medium", "Add concise testimonials near the CTA."))
    if visual.has_security_badges is False:
        blockers.append(Blocker("no_security_badges", ["No trust badges"], "medium", "Add security/SSL/privacy badges near forms."))
    if not text.cta_copy:
        blockers.append(Blocker("weak_cta_copy", ["CTA copy unclear"], "medium", "Add a primary CTA with a clear next action."))
    if visual.visual_clutter_level and visual.visual_clutter_level > 0.7:
        blockers.append(Blocker("high_clutter", ["Visual clutter high"], "medium", "Simplify layout and spacing."))

    trustScore = _clamp(trust)
    frictionScore = _clamp(friction)
    clarityScore = _clamp(clarity)

    # Decision probability: higher trust/clarity, lower friction
    decisionProbability = _clamp((trustScore * 0.4 + clarityScore * 0.4 + (100 - frictionScore) * 0.2)) / 100.0

    # Confidence heuristic: coverage of signals
    coverage = 0
    total = 6
    coverage += int(visual.has_logos is not None)
    coverage += int(visual.has_testimonials is not None)
    coverage += int(visual.has_pricing is not None)
    coverage += int(visual.visual_clutter_level is not None)
    coverage += int(visual.info_hierarchy_quality is not None)
    coverage += int(bool(text.key_lines))
    confidence = round(coverage / total, 2)

    # Quick wins and deep changes
    quick_wins = []
    deep_changes = []
    if visual.has_testimonials is False:
        quick_wins.append("Add 1-2 short testimonials near the primary CTA.")
    if visual.has_pricing is False:
        quick_wins.append("Add pricing or a clear 'See pricing' CTA.")
    if visual.cta_contrast_level is not None and visual.cta_contrast_level < 0.5:
        quick_wins.append("Increase CTA contrast and visual prominence.")
    if visual.visual_clutter_level and visual.visual_clutter_level > 0.7:
        deep_changes.append("Reduce visual clutter and simplify layout.")
    if visual.info_hierarchy_quality is not None and visual.info_hierarchy_quality < 0.4:
        deep_changes.append("Restructure information hierarchy and spacing.")

    return {
        "frictionScore": frictionScore,
        "trustScore": trustScore,
        "clarityScore": clarityScore,
        "decisionProbability": decisionProbability,
        "keyDecisionBlockers": [b.__dict__ for b in blockers],
        "recommendedQuickWins": quick_wins,
        "recommendedDeepChanges": deep_changes,
        "confidence": confidence,
    }








