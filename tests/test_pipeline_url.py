from fastapi.testclient import TestClient

from api.main import app
from api.schemas.page_features import PageFeatures

client = TestClient(app)


def test_brain_analyze_features_endpoint():
    payload = {
        "featuresSchemaVersion": "1.0",
        "visual": {
            "has_logos": True,
            "has_testimonials": False,
            "has_pricing": True,
            "visual_clutter_level": 0.4,
            "info_hierarchy_quality": 0.7,
            "cta_contrast_level": 0.6,
            "primary_cta_text": "Get started",
        },
        "text": {
            "key_lines": ["Example headline"],
            "offers": ["Save 20%"],
            "claims": ["Trusted by 1k customers"],
            "risk_reversal": [],
            "audience_clarity": "Marketers",
            "cta_copy": "Get started",
            "pricing_mentions": ["$"],
            "proof_points": ["Case studies"],
            "differentiators": [],
        },
        "meta": {"url": "http://example.com", "timestamp": "2025-01-01T00:00:00Z", "screenshot_bytes": 12345},
    }

    resp = client.post("/api/brain/analyze-features", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysisStatus"] == "ok"
    assert "brain" in data
    assert data["featuresSchemaVersion"] == "1.0"













