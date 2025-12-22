from api.brain.decision_brain import analyze_decision
from api.schemas.page_features import (
    PageFeatures,
    VisualFeatures,
    TextFeatures,
    MetaFeatures,
)


def make_features(**kwargs):
    visual = kwargs.get("visual", {})
    text = kwargs.get("text", {})
    meta = kwargs.get("meta", {})
    return PageFeatures(
        visual=VisualFeatures(**visual),
        text=TextFeatures(**text),
        meta=MetaFeatures(**meta),
    )


def test_low_trust_high_friction():
    features = make_features(
        visual={
            "has_logos": False,
            "has_testimonials": False,
            "has_pricing": False,
            "visual_clutter_level": 0.8,
            "info_hierarchy_quality": 0.3,
            "cta_contrast_level": 0.3,
        },
        text={"key_lines": [], "offers": [], "claims": [], "risk_reversal": []},
    )
    result = analyze_decision(features)
    assert result["trustScore"] < 50
    assert result["frictionScore"] > 50
    assert result["decisionProbability"] < 0.6


def test_high_trust_low_friction():
    features = make_features(
        visual={
            "has_logos": True,
            "has_testimonials": True,
            "has_pricing": True,
            "visual_clutter_level": 0.3,
            "info_hierarchy_quality": 0.8,
            "cta_contrast_level": 0.8,
        },
        text={
            "key_lines": ["Great product for marketers"],
            "offers": ["20% off launch"],
            "claims": ["Trusted by 10k customers"],
            "risk_reversal": ["30-day refund"],
            "audience_clarity": "Marketers",
            "cta_copy": "Get started",
        },
    )
    result = analyze_decision(features)
    assert result["trustScore"] > 60
    assert result["frictionScore"] < 50
    assert result["decisionProbability"] > 0.6
















