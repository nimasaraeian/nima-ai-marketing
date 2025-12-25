"""
Pricing Page Evidence Extraction

Extracts decision signals from pricing pages:
- Choice overload (too many options)
- Transparency level (clear vs hidden pricing)
- Risk exposure (commitment level)
- Commitment pressure (trial vs paid)

Focus: Decision psychology signals only, NOT pricing strategy or design.
"""

import re
import logging
from typing import Optional, Dict, Any, Literal
from bs4 import BeautifulSoup

from api.brain.decision_signals import DecisionSignals, create_empty_signals

logger = logging.getLogger("pricing_signals")


def _count_pricing_tiers(html: str) -> int:
    """
    Count number of pricing tiers/plans visible on the page.
    """
    if not html:
        return 0
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Common pricing tier selectors
        tier_selectors = [
            '[class*="pricing"] [class*="tier"]',
            '[class*="plan"]',
            '[class*="package"]',
            '[data-plan]',
            '[data-tier]',
        ]
        
        tier_count = 0
        for selector in tier_selectors:
            elements = soup.select(selector)
            if elements:
                tier_count = max(tier_count, len(elements))
        
        # Fallback: count price mentions
        if tier_count == 0:
            price_patterns = [
                r'\$\d+',
                r'\d+\s*(?:USD|EUR|GBP|per month|per year)',
            ]
            text = soup.get_text()
            matches = []
            for pattern in price_patterns:
                matches.extend(re.findall(pattern, text, re.I))
            # Estimate tiers from unique price mentions (rough heuristic)
            unique_prices = len(set(matches))
            tier_count = min(unique_prices, 5)  # Cap at 5
        
        return tier_count
    except Exception as e:
        logger.warning(f"Failed to count pricing tiers: {e}")
        return 0


def _analyze_choice_overload(html: str, text: str) -> Literal["low", "medium", "high"]:
    """
    Analyze choice overload from pricing page.
    
    High: 5+ tiers, complex comparisons, many features
    Medium: 3-4 tiers, moderate complexity
    Low: 1-2 tiers, simple structure
    """
    tier_count = _count_pricing_tiers(html) if html else 0
    
    # Also check for comparison tables, feature lists
    if text:
        text_lower = text.lower()
        
        # Complex comparison signals
        comparison_keywords = [
            "compare", "comparison", "vs", "versus", "difference",
            "feature", "features", "includes", "includes:", "what's included"
        ]
        
        comparison_count = sum(1 for keyword in comparison_keywords if keyword in text_lower)
        
        # Feature list complexity
        feature_list_patterns = [
            r'\d+\s+features?',
            r'feature\s+list',
            r'what\'s\s+included',
        ]
        feature_complexity = sum(1 for pattern in feature_list_patterns if re.search(pattern, text_lower, re.I))
        
        # Adjust based on complexity
        if tier_count >= 5 or comparison_count >= 3 or feature_complexity >= 2:
            return "high"
        elif tier_count >= 3 or comparison_count >= 1:
            return "medium"
        else:
            return "low"
    else:
        # Tier count only
        if tier_count >= 5:
            return "high"
        elif tier_count >= 3:
            return "medium"
        else:
            return "low"


def _analyze_transparency_level(html: str, text: str) -> Literal["low", "medium", "high"]:
    """
    Analyze pricing transparency.
    
    High: Clear prices, no hidden fees, simple structure
    Medium: Prices visible but some complexity
    Low: Hidden pricing, "contact sales", unclear structure
    """
    if not text:
        return "low"
    
    text_lower = text.lower()
    
    # High transparency signals
    transparent_patterns = [
        r'\$\d+[\d,.]*\s*(?:per|/)\s*(?:month|year|mo|yr)',
        r'pricing\s+starts\s+at',
        r'from\s+\$\d+',
        r'no\s+hidden\s+fees',
        r'all\s+prices\s+include',
    ]
    
    # Low transparency signals
    hidden_patterns = [
        r'contact\s+(?:sales|us|for\s+pricing)',
        r'custom\s+pricing',
        r'pricing\s+available\s+upon\s+request',
        r'request\s+a\s+quote',
        r'pricing\s+varies',
    ]
    
    transparent_count = sum(1 for pattern in transparent_patterns if re.search(pattern, text_lower))
    hidden_count = sum(1 for pattern in hidden_patterns if re.search(pattern, text_lower))
    
    if hidden_count >= 2:
        return "low"
    elif transparent_count >= 2:
        return "high"
    elif transparent_count >= 1:
        return "medium"
    else:
        return "medium"  # Default to medium if unclear


def _analyze_risk_exposure(html: str, text: str) -> Literal["low", "medium", "high"]:
    """
    Analyze risk exposure from pricing structure.
    
    High: Annual commitments, high prices, no trial
    Medium: Monthly with trial, moderate prices
    Low: Free tier, trial, low commitment
    """
    if not text:
        return "medium"
    
    text_lower = text.lower()
    
    # High risk signals
    high_risk_patterns = [
        r'annual\s+(?:commitment|plan|billing)',
        r'\$\d{3,}',  # Prices $100+
        r'no\s+(?:trial|refund|cancel)',
        r'commitment\s+required',
        r'contract',
    ]
    
    # Low risk signals
    low_risk_patterns = [
        r'free\s+(?:tier|plan|trial)',
        r'no\s+credit\s+card',
        r'cancel\s+anytime',
        r'money\s+back\s+guarantee',
        r'\d+\s+day\s+(?:trial|free)',
    ]
    
    high_risk_count = sum(1 for pattern in high_risk_patterns if re.search(pattern, text_lower))
    low_risk_count = sum(1 for pattern in low_risk_patterns if re.search(pattern, text_lower))
    
    if high_risk_count >= 2:
        return "high"
    elif low_risk_count >= 2:
        return "low"
    else:
        return "medium"


def _analyze_commitment_pressure(html: str, text: str) -> Literal["low", "medium", "high"]:
    """
    Analyze commitment pressure from pricing page.
    
    High: Strong CTAs, limited time, urgency
    Medium: Standard CTAs, some urgency
    Low: Soft CTAs, no urgency, trial-focused
    """
    if not text:
        return "low"
    
    text_lower = text.lower()
    
    # High pressure signals
    high_pressure_patterns = [
        r'(?:buy\s+now|purchase|get\s+started|sign\s+up)\s+(?:today|now)',
        r'limited\s+time',
        r'offer\s+expires',
        r'only\s+\d+\s+left',
    ]
    
    # Low pressure signals
    low_pressure_patterns = [
        r'start\s+free\s+trial',
        r'no\s+credit\s+card',
        r'explore\s+(?:plans|pricing)',
        r'learn\s+more',
        r'see\s+pricing',
    ]
    
    high_pressure_count = sum(1 for pattern in high_pressure_patterns if re.search(pattern, text_lower))
    low_pressure_count = sum(1 for pattern in low_pressure_patterns if re.search(pattern, text_lower))
    
    if high_pressure_count >= 2:
        return "high"
    elif low_pressure_count >= 2:
        return "low"
    else:
        return "medium"


def extract_pricing_signals(html: Optional[str] = None, text: Optional[str] = None) -> DecisionSignals:
    """
    Extract decision signals from pricing page.
    
    Args:
        html: HTML content of pricing page (optional)
        text: Plain text content of pricing page (optional)
        
    Returns:
        DecisionSignals with pricing-specific signals populated
    """
    if not html and not text:
        logger.warning("No pricing content provided for signal extraction")
        signals = create_empty_signals()
        signals.source = "pricing"
        signals.confidence = 0.0
        return signals
    
    # Extract text from HTML if needed
    if html and not text:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text()
        except Exception as e:
            logger.warning(f"Failed to extract text from HTML: {e}")
            text = ""
    
    # Analyze pricing-specific signals
    choice_overload = _analyze_choice_overload(html or "", text or "")
    transparency_level = _analyze_transparency_level(html or "", text or "")
    risk_exposure = _analyze_risk_exposure(html or "", text or "")
    commitment_pressure = _analyze_commitment_pressure(html or "", text or "")
    
    # Map pricing signals to DecisionSignals structure
    # choice_overload → cognitive_load
    cognitive_load = choice_overload
    
    # transparency_level → reassurance_level
    reassurance_level = transparency_level
    
    # commitment_pressure → pressure_level
    pressure_level = commitment_pressure
    
    # Default values for other signals
    promise_strength = "medium"  # Pricing pages don't typically show promise strength
    emotional_tone = "calm"  # Pricing pages are usually neutral
    
    # Calculate confidence
    confidence = 0.8 if (html or text) else 0.0
    
    # Build signals object
    signals = DecisionSignals(
        promise_strength=promise_strength,
        emotional_tone=emotional_tone,
        reassurance_level=reassurance_level,
        risk_exposure=risk_exposure,
        cognitive_load=cognitive_load,
        pressure_level=pressure_level,
        choice_overload=choice_overload,
        transparency_level=transparency_level,
        commitment_pressure=commitment_pressure,
        source="pricing",
        confidence=confidence,
        signals={
            "tier_count": _count_pricing_tiers(html or ""),
            "has_html": bool(html),
            "text_length": len(text or ""),
            "pricing_analysis": {
                "choice_overload": choice_overload,
                "transparency_level": transparency_level,
                "risk_exposure": risk_exposure,
                "commitment_pressure": commitment_pressure
            }
        }
    )
    
    logger.debug(
        f"Extracted pricing signals: choice_overload={choice_overload}, "
        f"transparency={transparency_level}, risk={risk_exposure}, pressure={commitment_pressure}"
    )
    
    return signals



