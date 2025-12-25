"""
Evidence Integration Module

Integrates Ad and Pricing evidence into the Decision Engine pipeline
without changing existing decision logic.

This module:
1. Extracts signals from all available evidence sources
2. Merges signals
3. Enriches explanations with evidence source information
4. Preserves existing Decision State resolver logic
"""

import logging
from typing import Optional, Dict, Any

from api.brain.decision_signals import DecisionSignals
from api.brain.evidence.landing_signals import extract_landing_signals
from api.brain.evidence.ad_signals import extract_ad_signals, AdInput
from api.brain.evidence.pricing_signals import extract_pricing_signals
from api.brain.evidence.signal_merger import merge_signals
from api.brain.evidence.explanation_builder import build_evidence_explanation

logger = logging.getLogger("evidence_integration")


class EvidenceContext:
    """
    Context for evidence extraction from multiple sources.
    """
    def __init__(
        self,
        landing_features=None,  # PageFeatures
        ad_input: Optional[AdInput] = None,
        pricing_html: Optional[str] = None,
        pricing_text: Optional[str] = None
    ):
        self.landing_features = landing_features
        self.ad_input = ad_input
        self.pricing_html = pricing_html
        self.pricing_text = pricing_text


def extract_all_evidence(context: EvidenceContext) -> Dict[str, Any]:
    """
    Extract signals from all available evidence sources.
    
    Args:
        context: EvidenceContext with available evidence sources
        
    Returns:
        Dict with:
        - landing_signals: DecisionSignals from landing page
        - ad_signals: DecisionSignals from ad (optional)
        - pricing_signals: DecisionSignals from pricing page (optional)
        - merged_signals: Merged DecisionSignals
        - confidence_score: Overall confidence (0.0-1.0)
    """
    landing_signals = None
    ad_signals = None
    pricing_signals = None
    
    # Extract landing signals
    if context.landing_features:
        try:
            landing_signals = extract_landing_signals(context.landing_features)
            logger.debug("Extracted landing signals")
        except Exception as e:
            logger.warning(f"Failed to extract landing signals: {e}")
    
    # Extract ad signals
    if context.ad_input:
        try:
            ad_signals = extract_ad_signals(context.ad_input)
            logger.debug("Extracted ad signals")
        except Exception as e:
            logger.warning(f"Failed to extract ad signals: {e}")
    
    # Extract pricing signals
    if context.pricing_html or context.pricing_text:
        try:
            pricing_signals = extract_pricing_signals(
                html=context.pricing_html,
                text=context.pricing_text
            )
            logger.debug("Extracted pricing signals")
        except Exception as e:
            logger.warning(f"Failed to extract pricing signals: {e}")
    
    # Merge signals
    merged_signals, confidence_score = merge_signals(
        landing_signals=landing_signals,
        ad_signals=ad_signals,
        pricing_signals=pricing_signals
    )
    
    return {
        "landing_signals": landing_signals,
        "ad_signals": ad_signals,
        "pricing_signals": pricing_signals,
        "merged_signals": merged_signals,
        "confidence_score": confidence_score
    }


def enrich_decision_output(
    decision_output: Dict[str, Any],
    evidence_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Enrich decision engine output with evidence information.
    
    This function adds evidence metadata to the output without changing
    the core decision logic or state definitions.
    
    Args:
        decision_output: Original decision engine output
        evidence_result: Result from extract_all_evidence()
        
    Returns:
        Enriched decision output with evidence metadata
    """
    # Build evidence explanation
    evidence_explanation = build_evidence_explanation(
        merged_signals=evidence_result["merged_signals"],
        landing_signals=evidence_result.get("landing_signals"),
        ad_signals=evidence_result.get("ad_signals"),
        pricing_signals=evidence_result.get("pricing_signals")
    )
    
    # Add evidence metadata to output
    enriched = decision_output.copy()
    
    # Add evidence section (non-breaking addition)
    enriched["evidence"] = {
        "sources_used": [
            s for s in ["landing", "ad", "pricing"]
            if evidence_result.get(f"{s}_signals")
        ],
        "explanation": evidence_explanation,
        "merged_signals": {
            "promise_strength": evidence_result["merged_signals"].promise_strength,
            "emotional_tone": evidence_result["merged_signals"].emotional_tone,
            "reassurance_level": evidence_result["merged_signals"].reassurance_level,
            "risk_exposure": evidence_result["merged_signals"].risk_exposure,
            "cognitive_load": evidence_result["merged_signals"].cognitive_load,
            "pressure_level": evidence_result["merged_signals"].pressure_level,
        },
        "confidence": evidence_result["confidence_score"]
    }
    
    # Optionally enrich the "why" field with evidence explanation
    # (only if it doesn't break existing format)
    if "why" in enriched:
        # Append evidence explanation as additional context
        enriched["why"] = f"{enriched['why']}\n\n{evidence_explanation}"
    
    logger.debug(f"Enriched decision output with evidence from {len(enriched['evidence']['sources_used'])} sources")
    
    return enriched



