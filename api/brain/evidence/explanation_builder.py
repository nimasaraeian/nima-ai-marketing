"""
Explanation Builder

Extends decision explanations to mention which evidence sources were used
and which signals influenced the decision most.
"""

import logging
from typing import Optional, List, Dict, Any

from api.brain.decision_signals import DecisionSignals

logger = logging.getLogger("explanation_builder")


def build_evidence_explanation(
    merged_signals: DecisionSignals,
    landing_signals: Optional[DecisionSignals] = None,
    ad_signals: Optional[DecisionSignals] = None,
    pricing_signals: Optional[DecisionSignals] = None
) -> str:
    """
    Build explanation text mentioning evidence sources and influential signals.
    
    Args:
        merged_signals: Merged signals from all sources
        landing_signals: Landing page signals (optional)
        ad_signals: Ad signals (optional)
        pricing_signals: Pricing signals (optional)
        
    Returns:
        Explanation text mentioning evidence sources
    """
    sources_used = []
    if landing_signals:
        sources_used.append("Landing")
    if ad_signals:
        sources_used.append("Ad")
    if pricing_signals:
        sources_used.append("Pricing")
    
    if not sources_used:
        sources_used = ["Landing"]  # Default
    
    # Identify most influential signals
    influential_signals = []
    
    # Check for high/low extremes that would influence decision
    if merged_signals.promise_strength in ["low", "high"]:
        influential_signals.append(f"{merged_signals.promise_strength} promise strength")
    
    if merged_signals.reassurance_level == "low":
        influential_signals.append("low reassurance")
    
    if merged_signals.risk_exposure == "high":
        influential_signals.append("high risk exposure")
    
    if merged_signals.cognitive_load == "high":
        influential_signals.append("high cognitive load")
    
    if merged_signals.pressure_level == "high":
        influential_signals.append("high pressure")
    
    # Build explanation
    parts = []
    
    # Sources used
    if len(sources_used) == 1:
        parts.append(f"This assessment is based on {sources_used[0].lower()} page analysis.")
    elif len(sources_used) == 2:
        parts.append(f"This assessment combines {sources_used[0].lower()} and {sources_used[1].lower()} evidence.")
    else:
        parts.append(f"This assessment combines evidence from {', '.join(sources_used[:-1])}, and {sources_used[-1]}.")
    
    # Influential signals
    if influential_signals:
        if len(influential_signals) == 1:
            parts.append(f"The analysis shows {influential_signals[0]}.")
        elif len(influential_signals) == 2:
            parts.append(f"The analysis shows {influential_signals[0]} and {influential_signals[1]}.")
        else:
            parts.append(f"Key signals include {', '.join(influential_signals[:-1])}, and {influential_signals[-1]}.")
    
    explanation = " ".join(parts)
    
    logger.debug(f"Built evidence explanation: {explanation}")
    
    return explanation


def enrich_decision_explanation(
    original_explanation: str,
    evidence_explanation: str
) -> str:
    """
    Enrich original decision explanation with evidence source information.
    
    Args:
        original_explanation: Original explanation from decision engine
        evidence_explanation: Evidence source explanation
        
    Returns:
        Enriched explanation
    """
    # Append evidence explanation to original
    enriched = f"{original_explanation}\n\n{evidence_explanation}"
    
    return enriched



