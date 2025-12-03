"""
Integration test ensuring the cognitive friction endpoint returns the advanced psychological view.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
API_DIR = PROJECT_ROOT / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from api.main import app
from cognitive_friction_engine import (
    CognitiveFrictionResult,
    build_psychology_dashboard_stub,
)
from psychology_engine import AdvancedPsychologicalView, build_default_advanced_view


client = TestClient(app)


def _make_cognitive_result() -> CognitiveFrictionResult:
    dashboard = build_psychology_dashboard_stub(
        friction_score=40,
        trust_score=60,
        summary="Stub dashboard",
        hotspots=["Hero"],
        friction_points=["CTA"],
    )
    return CognitiveFrictionResult(
        frictionScore=40,
        trustScore=60,
        emotionalClarityScore=55,
        motivationMatchScore=52,
        decisionProbability=0.45,
        conversionLiftEstimate=10.0,
        keyDecisionBlockers=["Missing proof"],
        emotionalResistanceFactors=[],
        cognitiveOverloadFactors=[],
        trustBreakpoints=[],
        motivationMisalignments=[],
        recommendedQuickWins=["Add testimonial"],
        recommendedDeepChanges=["Rework narrative"],
        explanationSummary="Stub summary",
        psychology_dashboard=dashboard,
    )


def _make_advanced_view() -> AdvancedPsychologicalView:
    view = build_default_advanced_view()
    view.personality_activation.openness = 77
    view.attention_map.hotspots = ["Hero section", "CTA"]
    view.attention_map.friction_points = ["Pricing"]
    return view


def test_cognitive_friction_endpoint_includes_advanced_view():
    payload = {
        "raw_text": "Sample landing page copy highlighting value and CTA.",
        "platform": "landing_page",
        "goal": ["leads"],
        "audience": "cold",
        "language": "en",
    }

    with patch(
        "api.main.analyze_cognitive_friction",
        side_effect=lambda *args, **kwargs: _make_cognitive_result(),
    ), patch(
        "api.main.analyze_advanced_psychology",
        side_effect=lambda *args, **kwargs: _make_advanced_view(),
    ):
        response = client.post("/api/brain/cognitive-friction", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "psychology" in data
    advanced_view = data["psychology"]["advanced_view"]
    assert advanced_view["personality_activation"]["openness"] == 77
    assert isinstance(advanced_view["attention_map"]["hotspots"], list)
    assert advanced_view["attention_map"]["hotspots"][0] == "Hero section"

