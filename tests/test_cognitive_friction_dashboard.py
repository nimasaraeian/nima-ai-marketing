"""
Unit tests for psychology dashboard integration in cognitive friction analysis.
"""

from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_DIR = PROJECT_ROOT / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from cognitive_friction_engine import (
    CognitiveFrictionInput,
    analyze_cognitive_friction,
)


def _fake_client(payload: dict[str, object]):
    """Build a fake OpenAI client returning the provided payload."""
    message = SimpleNamespace(content=json.dumps(payload))
    choice = SimpleNamespace(message=message)
    response = SimpleNamespace(choices=[choice])

    class FakeCompletions:
        def create(self, **kwargs):
            return response

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    client = SimpleNamespace(chat=FakeChat())
    return client


def _sample_dashboard_payload() -> dict[str, object]:
    return {
        "frictionScore": 42,
        "trustScore": 58,
        "emotionalClarityScore": 64,
        "motivationMatchScore": 61,
        "decisionProbability": 0.43,
        "conversionLiftEstimate": 18,
        "keyDecisionBlockers": ["Lacks proof"],
        "emotionalResistanceFactors": ["Doubt"],
        "cognitiveOverloadFactors": [],
        "trustBreakpoints": ["No testimonials"],
        "motivationMisalignments": [],
        "recommendedQuickWins": ["Add fast social proof"],
        "recommendedDeepChanges": ["Reframe CTA"],
        "explanationSummary": "Sample summary.",
        "psychology_dashboard": {
            "personality_activation": {
                "O": 55,
                "C": 62,
                "E": 48,
                "A": 60,
                "N": 40,
                "dominant_profile": "Balanced Analyst",
                "explanation": "Emphasizes clarity and proof.",
            },
            "cognitive_style": {
                "type": "analytical",
                "overload_risk": 35,
                "ambiguity_aversion": 70,
                "explanation": "Needs more structure.",
            },
            "emotional_response": {
                "curiosity": 65,
                "excitement": 38,
                "motivation": 52,
                "anxiety": 42,
                "confusion": 30,
                "trust": 55,
            },
            "decision_frame": {
                "mode": "gain_seeking",
                "risk_style": "moderate",
                "decision_tendency": "hesitate",
                "explanation": "Interested but unsure.",
            },
            "trust_dynamics": {
                "visual_trust": 60,
                "institutional_trust": 50,
                "social_trust": 45,
                "skepticism": 40,
            },
            "motivation_style": {
                "primary": "Achievement",
                "secondary": "Security",
                "explanation": "Wants tangible outcomes with safety.",
            },
            "cognitive_load": {
                "clarity_score": 58,
                "overload_score": 32,
                "ambiguity_score": 44,
            },
            "behavioral_prediction": {
                "convert": 28,
                "hesitate": 45,
                "bounce": 15,
                "postpone": 12,
                "summary": "Most will hesitate pending proof.",
            },
            "attention_map": {
                "hotspots": ["Hero headline", "Pricing section"],
                "friction_points": ["Trust badges"],
            },
            "emotional_triggers": {
                "activated": ["Growth", "Curiosity"],
                "missing": ["Safety"],
            },
            "memory_activation": {
                "semantic": 60,
                "emotional": 52,
                "pattern": 41,
            },
            "risk_perception": {
                "risk_level": 55,
                "uncertainty_points": ["Lack of case studies"],
            },
            "cta_match": {
                "fit_score": 50,
                "clarity": 62,
                "motivation_alignment": 45,
                "action_probability": 40,
            },
        },
    }


class PsychologyDashboardTest(unittest.TestCase):
    """Test suite for psychology dashboard integration."""

    def test_analyze_cognitive_friction_returns_dashboard(self):
        """Ensure analyze_cognitive_friction returns the psychology dashboard when provided."""
        input_data = CognitiveFrictionInput(
            raw_text="Test landing page copy",
            platform="landing_page",
            goal=["leads"],
            audience="cold",
            language="en",
            meta={},
        )

        payload = _sample_dashboard_payload()
        fake_client = _fake_client(payload)

        with patch("cognitive_friction_engine.get_client", return_value=fake_client):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                result = analyze_cognitive_friction(input_data)

        self.assertIsNotNone(result.psychology_dashboard)
        self.assertEqual(result.psychology_dashboard.behavioral_prediction.convert, 28)
        self.assertIn(
            "Hero headline",
            result.psychology_dashboard.attention_map.hotspots,
        )


if __name__ == "__main__":
    unittest.main()

