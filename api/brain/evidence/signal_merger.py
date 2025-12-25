"""
Signal Aggregation Module

Merges decision signals from multiple evidence sources:
- Landing Page (baseline, highest trust)
- Ad/Banner (adjusts intensity)
- Pricing Page (adjusts intensity)

Rules:
- Landing signals are baseline (highest trust)
- Ad + Pricing only ADJUST intensity, never override blindly
- If multiple signals conflict, keep both and increase uncertainty
"""

import logging
from typing import Optional, Dict, Any, Literal, Tuple

from api.brain.decision_signals import DecisionSignals, create_empty_signals

logger = logging.getLogger("signal_merger")


def _merge_level(
    landing: str,
    ad: Optional[str] = None,
    pricing: Optional[str] = None
) -> Tuple[str, float]:
    """
    Merge a single signal level from multiple sources.
    
    Returns:
        (merged_level, confidence_adjustment)
        confidence_adjustment: -0.1 to +0.1 based on agreement
    """
    # Landing is baseline
    if not landing:
        landing = "medium"
    
    # If no other sources, return landing as-is
    if not ad and not pricing:
        return landing, 0.0
    
    # Convert to numeric for comparison
    level_map = {"low": 1, "medium": 2, "high": 3}
    reverse_map = {1: "low", 2: "medium", 3: "high"}
    
    landing_val = level_map.get(landing, 2)
    ad_val = level_map.get(ad, None) if ad else None
    pricing_val = level_map.get(pricing, None) if pricing else None
    
    # Calculate weighted average
    # Landing: 60% weight (baseline, highest trust)
    # Ad: 20% weight (adjustment)
    # Pricing: 20% weight (adjustment)
    
    total_weight = 0.6
    weighted_sum = landing_val * 0.6
    
    if ad_val is not None:
        weighted_sum += ad_val * 0.2
        total_weight += 0.2
    
    if pricing_val is not None:
        weighted_sum += pricing_val * 0.2
        total_weight += 0.2
    
    # Round to nearest level
    merged_val = round(weighted_sum / total_weight)
    merged_val = max(1, min(3, merged_val))  # Clamp to 1-3
    merged_level = reverse_map[merged_val]
    
    # Calculate confidence adjustment based on agreement
    # If all sources agree, confidence increases
    # If sources conflict, confidence decreases
    values = [v for v in [landing_val, ad_val, pricing_val] if v is not None]
    if len(values) > 1:
        variance = max(values) - min(values)
        if variance == 0:
            confidence_adjustment = +0.05  # All agree
        elif variance == 1:
            confidence_adjustment = 0.0  # Moderate disagreement
        else:
            confidence_adjustment = -0.1  # Strong disagreement
    else:
        confidence_adjustment = 0.0
    
    return merged_level, confidence_adjustment


def merge_signals(
    landing_signals: Optional[DecisionSignals] = None,
    ad_signals: Optional[DecisionSignals] = None,
    pricing_signals: Optional[DecisionSignals] = None
) -> Tuple[DecisionSignals, float]:
    """
    Merge signals from multiple evidence sources.
    
    Args:
        landing_signals: Landing page signals (baseline, highest trust)
        ad_signals: Ad/banner signals (optional, adjusts intensity)
        pricing_signals: Pricing page signals (optional, adjusts intensity)
        
    Returns:
        (merged_signals, confidence_score)
        confidence_score: 0.0-1.0 based on signal agreement
    """
    # If no landing signals, create empty ones
    if not landing_signals:
        landing_signals = create_empty_signals()
        landing_signals.source = "landing"
    
    # Merge each signal level
    promise_strength, conf_adj_1 = _merge_level(
        landing_signals.promise_strength,
        ad_signals.promise_strength if ad_signals else None,
        None  # Pricing doesn't affect promise_strength
    )
    
    emotional_tone, conf_adj_2 = _merge_level(
        landing_signals.emotional_tone,
        ad_signals.emotional_tone if ad_signals else None,
        None  # Pricing doesn't affect emotional_tone
    )
    
    reassurance_level, conf_adj_3 = _merge_level(
        landing_signals.reassurance_level,
        ad_signals.reassurance_level if ad_signals else None,
        pricing_signals.reassurance_level if pricing_signals else None
    )
    
    risk_exposure, conf_adj_4 = _merge_level(
        landing_signals.risk_exposure,
        None,  # Ads don't typically show risk
        pricing_signals.risk_exposure if pricing_signals else None
    )
    
    cognitive_load, conf_adj_5 = _merge_level(
        landing_signals.cognitive_load,
        None,  # Ads are usually simple
        pricing_signals.cognitive_load if pricing_signals else None
    )
    
    pressure_level, conf_adj_6 = _merge_level(
        landing_signals.pressure_level,
        ad_signals.pressure_level if ad_signals else None,
        pricing_signals.pressure_level if pricing_signals else None
    )
    
    # Calculate overall confidence
    base_confidence = landing_signals.confidence or 0.7
    confidence_adjustments = [conf_adj_1, conf_adj_2, conf_adj_3, conf_adj_4, conf_adj_5, conf_adj_6]
    avg_adjustment = sum(confidence_adjustments) / len(confidence_adjustments)
    confidence_score = max(0.0, min(1.0, base_confidence + avg_adjustment))
    
    # Build merged signals
    merged = DecisionSignals(
        promise_strength=promise_strength,
        emotional_tone=emotional_tone,
        reassurance_level=reassurance_level,
        risk_exposure=risk_exposure,
        cognitive_load=cognitive_load,
        pressure_level=pressure_level,
        expectation_gap=ad_signals.expectation_gap if ad_signals else None,
        choice_overload=pricing_signals.choice_overload if pricing_signals else None,
        transparency_level=pricing_signals.transparency_level if pricing_signals else None,
        commitment_pressure=pricing_signals.commitment_pressure if pricing_signals else None,
        source="merged",
        confidence=confidence_score,
        signals={
            "sources_used": [
                s for s in ["landing", "ad", "pricing"]
                if (s == "landing" and landing_signals) or
                   (s == "ad" and ad_signals) or
                   (s == "pricing" and pricing_signals)
            ],
            "landing_signals": landing_signals.signals if landing_signals.signals else {},
            "ad_signals": ad_signals.signals if ad_signals and ad_signals.signals else {},
            "pricing_signals": pricing_signals.signals if pricing_signals and pricing_signals.signals else {},
            "confidence_adjustments": {
                "promise_strength": conf_adj_1,
                "emotional_tone": conf_adj_2,
                "reassurance_level": conf_adj_3,
                "risk_exposure": conf_adj_4,
                "cognitive_load": conf_adj_5,
                "pressure_level": conf_adj_6,
            }
        }
    )
    
    logger.info(
        f"Merged signals from {len([s for s in [landing_signals, ad_signals, pricing_signals] if s])} sources. "
        f"Confidence: {confidence_score:.2f}"
    )
    
    return merged, confidence_score

