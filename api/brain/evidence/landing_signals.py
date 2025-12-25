"""
Landing Page Evidence Extraction

Extracts decision signals from existing landing page analysis.
This module wraps the existing decision_brain.py logic to produce DecisionSignals.
"""

import logging
from typing import Optional, Dict, Any

from api.schemas.page_features import PageFeatures
from api.brain.decision_brain import analyze_decision
from api.brain.decision_signals import DecisionSignals, create_empty_signals

logger = logging.getLogger("landing_signals")


def _score_to_level(score: float, low_threshold: float = 40.0, high_threshold: float = 60.0) -> str:
    """
    Convert numeric score (0-100) to level (low/medium/high).
    
    Args:
        score: Numeric score 0-100
        low_threshold: Below this = low
        high_threshold: Above this = high
        
    Returns:
        "low", "medium", or "high"
    """
    if score < low_threshold:
        return "low"
    elif score > high_threshold:
        return "high"
    else:
        return "medium"


def extract_landing_signals(features: PageFeatures) -> DecisionSignals:
    """
    Extract decision signals from landing page features.
    
    This function uses the existing analyze_decision() logic to extract
    signals in the unified DecisionSignals format.
    
    Args:
        features: PageFeatures from existing landing page analysis
        
    Returns:
        DecisionSignals with landing page signals populated
    """
    # Use existing decision brain analysis
    analysis = analyze_decision(features)
    
    # Map existing scores to DecisionSignals
    trust_score = analysis.get("trustScore", 50.0)
    friction_score = analysis.get("frictionScore", 50.0)
    clarity_score = analysis.get("clarityScore", 50.0)
    decision_probability = analysis.get("decisionProbability", 0.5)
    
    # Map to signal levels
    # Trust score → reassurance_level
    reassurance_level = _score_to_level(trust_score)
    
    # Friction score → cognitive_load (inverse: high friction = high cognitive load)
    # Also maps to pressure_level (high friction can indicate pressure)
    cognitive_load = _score_to_level(100 - friction_score)  # Inverse
    pressure_level = "low" if friction_score < 40 else ("high" if friction_score > 60 else "medium")
    
    # Clarity score → promise_strength
    promise_strength = _score_to_level(clarity_score)
    
    # Risk exposure: infer from guarantee, security badges, testimonials
    visual = features.visual
    has_guarantee = visual.has_guarantee or False
    has_security = visual.has_security_badges or False
    has_testimonials = visual.has_testimonials or False
    
    risk_signals = sum([has_guarantee, has_security, has_testimonials])
    if risk_signals >= 2:
        risk_exposure = "low"
    elif risk_signals >= 1:
        risk_exposure = "medium"
    else:
        risk_exposure = "high"
    
    # Emotional tone: infer from CTA copy and visual style
    # Default to "calm" for landing pages (they're usually neutral)
    emotional_tone = "calm"
    
    # Check CTA copy for urgency
    if features.text.cta_copy:
        cta_lower = features.text.cta_copy.lower()
        if any(word in cta_lower for word in ["now", "today", "hurry", "limited"]):
            emotional_tone = "urgent"
        elif any(word in cta_lower for word in ["free", "safe", "guaranteed"]):
            emotional_tone = "reassuring"
    
    # Calculate confidence from decision probability
    confidence = decision_probability
    
    # Build signals object
    signals = DecisionSignals(
        promise_strength=promise_strength,
        emotional_tone=emotional_tone,
        reassurance_level=reassurance_level,
        risk_exposure=risk_exposure,
        cognitive_load=cognitive_load,
        pressure_level=pressure_level,
        source="landing",
        confidence=confidence,
        signals={
            "trust_score": trust_score,
            "friction_score": friction_score,
            "clarity_score": clarity_score,
            "decision_probability": decision_probability,
            "has_guarantee": has_guarantee,
            "has_security": has_security,
            "has_testimonials": has_testimonials,
            "blockers": analysis.get("keyDecisionBlockers", []),
            "quick_wins": analysis.get("recommendedQuickWins", []),
            "deep_changes": analysis.get("recommendedDeepChanges", [])
        }
    )
    
    logger.debug(
        f"Extracted landing signals: promise={promise_strength}, "
        f"reassurance={reassurance_level}, risk={risk_exposure}, "
        f"cognitive_load={cognitive_load}"
    )
    
    return signals



