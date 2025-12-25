"""
Tests for Evidence Extraction Modules

Tests for:
- Ad signal extraction
- Pricing signal extraction
- Signal merging
- Landing signal extraction
"""

import pytest
from api.brain.evidence.ad_signals import extract_ad_signals, AdInput
from api.brain.evidence.pricing_signals import extract_pricing_signals
from api.brain.evidence.signal_merger import merge_signals
from api.brain.evidence.landing_signals import extract_landing_signals
from api.brain.decision_signals import DecisionSignals, create_empty_signals
from api.schemas.page_features import PageFeatures, VisualFeatures, TextFeatures, MetaFeatures


def test_extract_ad_signals_high_promise():
    """Test ad signal extraction with high promise ad copy."""
    ad_input = AdInput(
        ad_copy="Get 50% more leads in 30 days. Guaranteed results or your money back.",
        ad_headline="Boost Your Sales Today"
    )
    
    signals = extract_ad_signals(ad_input)
    
    assert signals.promise_strength == "high"
    assert signals.emotional_tone in ["urgent", "reassuring"]
    assert signals.pressure_level in ["medium", "high"]
    assert signals.reassurance_level in ["medium", "high"]
    assert signals.source == "ad"
    assert signals.confidence > 0.0


def test_extract_ad_signals_low_promise():
    """Test ad signal extraction with vague ad copy."""
    ad_input = AdInput(
        ad_copy="Improve your business with our solution.",
        ad_headline="Better Results"
    )
    
    signals = extract_ad_signals(ad_input)
    
    assert signals.promise_strength in ["low", "medium"]
    assert signals.source == "ad"


def test_extract_pricing_signals_high_choice_overload():
    """Test pricing signal extraction with many tiers."""
    html = """
    <div class="pricing">
        <div class="plan">Plan 1</div>
        <div class="plan">Plan 2</div>
        <div class="plan">Plan 3</div>
        <div class="plan">Plan 4</div>
        <div class="plan">Plan 5</div>
    </div>
    """
    
    signals = extract_pricing_signals(html=html)
    
    assert signals.choice_overload == "high"
    assert signals.cognitive_load == "high"
    assert signals.source == "pricing"


def test_extract_pricing_signals_low_transparency():
    """Test pricing signal extraction with hidden pricing."""
    text = "Contact sales for custom pricing. Pricing varies by requirements."
    
    signals = extract_pricing_signals(text=text)
    
    assert signals.transparency_level == "low"
    assert signals.reassurance_level == "low"
    assert signals.source == "pricing"


def test_merge_signals_landing_only():
    """Test signal merging with only landing signals."""
    landing = DecisionSignals(
        promise_strength="high",
        emotional_tone="calm",
        reassurance_level="medium",
        risk_exposure="low",
        cognitive_load="medium",
        pressure_level="low",
        source="landing",
        confidence=0.8
    )
    
    merged, confidence = merge_signals(landing_signals=landing)
    
    assert merged.promise_strength == "high"
    assert merged.source == "merged"
    assert confidence > 0.0


def test_merge_signals_landing_and_ad():
    """Test signal merging with landing and ad signals."""
    landing = DecisionSignals(
        promise_strength="medium",
        emotional_tone="calm",
        reassurance_level="medium",
        risk_exposure="medium",
        cognitive_load="medium",
        pressure_level="low",
        source="landing",
        confidence=0.7
    )
    
    ad = DecisionSignals(
        promise_strength="high",
        emotional_tone="urgent",
        reassurance_level="high",
        risk_exposure="medium",
        cognitive_load="low",
        pressure_level="high",
        source="ad",
        confidence=0.7
    )
    
    merged, confidence = merge_signals(landing_signals=landing, ad_signals=ad)
    
    # Landing has 60% weight, ad has 20% weight
    # So merged should be closer to landing but adjusted by ad
    assert merged.source == "merged"
    assert confidence > 0.0


def test_merge_signals_all_sources():
    """Test signal merging with all three sources."""
    landing = DecisionSignals(
        promise_strength="medium",
        emotional_tone="calm",
        reassurance_level="medium",
        risk_exposure="medium",
        cognitive_load="medium",
        pressure_level="low",
        source="landing",
        confidence=0.7
    )
    
    ad = DecisionSignals(
        promise_strength="high",
        emotional_tone="urgent",
        reassurance_level="high",
        risk_exposure="medium",
        cognitive_load="low",
        pressure_level="high",
        source="ad",
        confidence=0.7
    )
    
    pricing = DecisionSignals(
        promise_strength="medium",
        emotional_tone="calm",
        reassurance_level="low",
        risk_exposure="high",
        cognitive_load="high",
        pressure_level="medium",
        source="pricing",
        confidence=0.8
    )
    
    merged, confidence = merge_signals(
        landing_signals=landing,
        ad_signals=ad,
        pricing_signals=pricing
    )
    
    assert merged.source == "merged"
    assert "landing" in merged.signals["sources_used"]
    assert "ad" in merged.signals["sources_used"]
    assert "pricing" in merged.signals["sources_used"]
    assert confidence > 0.0


def test_extract_landing_signals():
    """Test landing signal extraction from PageFeatures."""
    features = PageFeatures(
        visual=VisualFeatures(
            has_testimonials=True,
            has_security_badges=True,
            has_guarantee=True,
            visual_clutter_level=0.3,
            info_hierarchy_quality=0.8
        ),
        text=TextFeatures(
            cta_copy="Start Free Trial",
            offers=["Free 14-day trial"],
            proof_points=["Trusted by 1000+ companies"]
        ),
        meta=MetaFeatures()
    )
    
    signals = extract_landing_signals(features)
    
    assert signals.source == "landing"
    assert signals.reassurance_level in ["medium", "high"]  # Has trust signals
    assert signals.risk_exposure == "low"  # Has guarantee, security, testimonials
    assert signals.confidence > 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



