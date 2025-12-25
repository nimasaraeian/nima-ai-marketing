"""
Ad / Banner Evidence Extraction

Extracts psychological decision signals from:
- Ad images (banner, billboard, screenshot)
- Ad copy (text-only ads)

Focus: Decision psychology signals only, NOT design quality or creativity.
"""

import re
import logging
from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass

from api.brain.decision_signals import DecisionSignals, create_empty_signals

logger = logging.getLogger("ad_signals")


@dataclass
class AdInput:
    """Input for ad signal extraction"""
    image_url: Optional[str] = None
    image_bytes: Optional[bytes] = None
    ad_copy: Optional[str] = None
    ad_headline: Optional[str] = None
    ad_description: Optional[str] = None


def _analyze_promise_strength(text: str) -> Literal["low", "medium", "high"]:
    """
    Analyze promise strength from ad copy.
    
    High: Specific, concrete outcomes ("Get 50% more leads")
    Medium: General benefits ("Improve your business")
    Low: Vague or unclear promises
    """
    if not text:
        return "low"
    
    text_lower = text.lower()
    
    # High promise signals
    high_signals = [
        r'\d+%',  # Percentages
        r'\$\d+',  # Dollar amounts
        r'\d+\s*(?:more|less|faster|better)',  # Quantified improvements
        r'(?:guarantee|guaranteed|promise|assure)',  # Strong commitment
        r'(?:free|no cost|zero risk)',  # Risk-free promises
    ]
    
    # Medium promise signals
    medium_signals = [
        r'(?:improve|increase|boost|enhance|better|best)',  # Improvement words
        r'(?:save|earn|get|gain)',  # Benefit words
        r'(?:solution|help|support)',  # Supportive language
    ]
    
    high_count = sum(1 for pattern in high_signals if re.search(pattern, text_lower))
    medium_count = sum(1 for pattern in medium_signals if re.search(pattern, text_lower))
    
    if high_count >= 2:
        return "high"
    elif high_count >= 1 or medium_count >= 2:
        return "medium"
    else:
        return "low"


def _analyze_emotional_tone(text: str) -> Literal["calm", "urgent", "aggressive", "reassuring"]:
    """
    Analyze emotional tone from ad copy.
    
    Urgent: Time pressure, scarcity, FOMO
    Aggressive: Pushy, demanding, high pressure
    Reassuring: Safe, trusted, comfortable
    Calm: Neutral, informative
    """
    if not text:
        return "calm"
    
    text_lower = text.lower()
    
    # Urgent signals
    urgent_patterns = [
        r'(?:limited time|act now|hurry|expires|ending soon|last chance)',
        r'(?:today only|this week|don\'t miss|before it\'s too late)',
        r'(?:only \d+ left|few remaining|almost gone)',
    ]
    
    # Aggressive signals
    aggressive_patterns = [
        r'(?:must|have to|need to|required|mandatory)',
        r'(?:stop|quit|avoid|never|don\'t)',
        r'(?:urgent|critical|immediate|now)',
    ]
    
    # Reassuring signals
    reassuring_patterns = [
        r'(?:trusted|safe|secure|guaranteed|proven|tested)',
        r'(?:easy|simple|quick|fast|effortless)',
        r'(?:free|no risk|no obligation|cancel anytime)',
        r'(?:satisfaction|money back|refund)',
    ]
    
    urgent_count = sum(1 for pattern in urgent_patterns if re.search(pattern, text_lower))
    aggressive_count = sum(1 for pattern in aggressive_patterns if re.search(pattern, text_lower))
    reassuring_count = sum(1 for pattern in reassuring_patterns if re.search(pattern, text_lower))
    
    if aggressive_count >= 2:
        return "aggressive"
    elif urgent_count >= 2:
        return "urgent"
    elif reassuring_count >= 2:
        return "reassuring"
    else:
        return "calm"


def _analyze_pressure_level(text: str) -> Literal["low", "medium", "high"]:
    """
    Analyze pressure/urgency level from ad copy.
    """
    if not text:
        return "low"
    
    text_lower = text.lower()
    
    # High pressure signals
    high_pressure = [
        r'(?:now|immediately|right now|today|this instant)',
        r'(?:limited|scarcity|running out|almost gone)',
        r'(?:act now|don\'t wait|hurry|expires)',
        r'(?:only \d+|few left|last chance)',
    ]
    
    # Medium pressure signals
    medium_pressure = [
        r'(?:soon|quickly|fast|don\'t miss)',
        r'(?:special|exclusive|one-time)',
    ]
    
    high_count = sum(1 for pattern in high_pressure if re.search(pattern, text_lower))
    medium_count = sum(1 for pattern in medium_pressure if re.search(pattern, text_lower))
    
    if high_count >= 2:
        return "high"
    elif high_count >= 1 or medium_count >= 1:
        return "medium"
    else:
        return "low"


def _analyze_reassurance_level(text: str) -> Literal["low", "medium", "high"]:
    """
    Analyze reassurance level from ad copy.
    """
    if not text:
        return "low"
    
    text_lower = text.lower()
    
    # High reassurance signals
    reassurance_patterns = [
        r'(?:guarantee|guaranteed|promise|assure|assured)',
        r'(?:free|no cost|no risk|no obligation)',
        r'(?:money back|refund|satisfaction|trial)',
        r'(?:trusted|proven|tested|verified|certified)',
        r'(?:safe|secure|protected|insured)',
    ]
    
    count = sum(1 for pattern in reassurance_patterns if re.search(pattern, text_lower))
    
    if count >= 3:
        return "high"
    elif count >= 1:
        return "medium"
    else:
        return "low"


def _analyze_expectation_gap(text: str) -> Literal["low", "medium", "high"]:
    """
    Analyze expectation gap (promise vs reality risk).
    
    High: Overpromising, unrealistic claims
    Medium: Moderate claims
    Low: Realistic, grounded promises
    """
    if not text:
        return "medium"
    
    text_lower = text.lower()
    
    # Overpromising signals
    overpromise_patterns = [
        r'(?:instant|immediate|overnight|in minutes)',
        r'(?:guaranteed|100%|always|never fails)',
        r'(?:miracle|magic|secret|hidden)',
        r'(?:#1|best|top|leading|world\'s best)',
    ]
    
    # Realistic signals
    realistic_patterns = [
        r'(?:may|might|could|possible|potential)',
        r'(?:typically|usually|often|generally)',
        r'(?:results may vary|individual results)',
    ]
    
    overpromise_count = sum(1 for pattern in overpromise_patterns if re.search(pattern, text_lower))
    realistic_count = sum(1 for pattern in realistic_patterns if re.search(pattern, text_lower))
    
    if overpromise_count >= 3:
        return "high"
    elif realistic_count >= 1:
        return "low"
    else:
        return "medium"


def extract_ad_signals(input_data: AdInput) -> DecisionSignals:
    """
    Extract decision signals from ad/banner content.
    
    Args:
        input_data: AdInput with image or text content
        
    Returns:
        DecisionSignals with ad-specific signals populated
    """
    # Combine all text sources
    all_text = " ".join(filter(None, [
        input_data.ad_copy or "",
        input_data.ad_headline or "",
        input_data.ad_description or ""
    ]))
    
    # If no text and no image, return empty signals
    if not all_text and not input_data.image_url and not input_data.image_bytes:
        logger.warning("No ad content provided for signal extraction")
        signals = create_empty_signals()
        signals.source = "ad"
        signals.confidence = 0.0
        return signals
    
    # Analyze text signals
    promise_strength = _analyze_promise_strength(all_text)
    emotional_tone = _analyze_emotional_tone(all_text)
    pressure_level = _analyze_pressure_level(all_text)
    reassurance_level = _analyze_reassurance_level(all_text)
    expectation_gap = _analyze_expectation_gap(all_text)
    
    # Default values for signals not directly extractable from text
    risk_exposure = "medium"  # Ads typically don't show risk explicitly
    cognitive_load = "low"  # Ads are usually simple
    
    # Calculate confidence based on content availability
    confidence = 0.7 if all_text else 0.3
    
    # Build signals object
    signals = DecisionSignals(
        promise_strength=promise_strength,
        emotional_tone=emotional_tone,
        reassurance_level=reassurance_level,
        risk_exposure=risk_exposure,
        cognitive_load=cognitive_load,
        pressure_level=pressure_level,
        expectation_gap=expectation_gap,
        source="ad",
        confidence=confidence,
        signals={
            "ad_copy_length": len(all_text),
            "has_image": bool(input_data.image_url or input_data.image_bytes),
            "text_analysis": {
                "promise_strength": promise_strength,
                "emotional_tone": emotional_tone,
                "pressure_level": pressure_level,
                "reassurance_level": reassurance_level,
                "expectation_gap": expectation_gap
            }
        }
    )
    
    logger.debug(f"Extracted ad signals: promise={promise_strength}, tone={emotional_tone}, pressure={pressure_level}")
    
    return signals



