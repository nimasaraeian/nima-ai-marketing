"""
Unit/integration tests for /api/analyze/url-human endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_test_capture_endpoint():
    """
    Test /api/analyze/url-human/test-capture endpoint.
    
    Asserts:
    1) HTTP 200
    2) JSON contains analysisStatus == "ok"
    3) human_report is a non-empty string (if present)
    """
    payload = {
        "url": "https://example.com",
        "goal": "leads"
    }
    
    response = client.post("/api/analyze/url-human/test-capture", json=payload)
    
    # Assert 1: HTTP 200
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    # Parse JSON
    data = response.json()
    
    # Assert 2: JSON contains analysisStatus == "ok"
    assert "analysisStatus" in data, "Response must contain 'analysisStatus' field"
    assert data["analysisStatus"] == "ok", f"Expected analysisStatus='ok', got '{data['analysisStatus']}'"
    
    # Assert 3: If human_report is present, it should be a non-empty string
    # Note: test-capture doesn't generate human_report, but we check if it exists
    if "human_report" in data:
        assert isinstance(data["human_report"], str), "human_report must be a string"
        assert len(data["human_report"]) > 0, "human_report must be non-empty"


def test_analyze_url_human_endpoint():
    """
    Test /api/analyze/url-human endpoint (full analysis).
    
    Asserts:
    1) HTTP 200
    2) JSON contains analysisStatus == "ok"
    3) human_report is a non-empty string
    """
    payload = {
        "url": "https://example.com",
        "goal": "leads",
        "locale": "en"
    }
    
    response = client.post("/api/analyze/url-human", json=payload)
    
    # Assert 1: HTTP 200
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    # Parse JSON
    data = response.json()
    
    # Assert 2: JSON contains analysisStatus == "ok"
    assert "analysisStatus" in data, "Response must contain 'analysisStatus' field"
    assert data["analysisStatus"] == "ok", f"Expected analysisStatus='ok', got '{data['analysisStatus']}'"
    
    # Assert 3: human_report is a non-empty string
    assert "human_report" in data, "Response must contain 'human_report' field"
    assert isinstance(data["human_report"], str), "human_report must be a string"
    assert len(data["human_report"]) > 0, "human_report must be non-empty"


def test_analyze_url_human_error_handling():
    """
    Test error handling in /api/analyze/url-human/test-capture.
    
    Asserts that errors return analysisStatus == "error"
    """
    # Use an invalid URL that will likely fail
    payload = {
        "url": "not-a-valid-url",
        "goal": "leads"
    }
    
    response = client.post("/api/analyze/url-human/test-capture", json=payload)
    
    # Should still return 200 (we changed error handling to return JSON)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    
    # Should have analysisStatus == "error"
    assert "analysisStatus" in data, "Response must contain 'analysisStatus' field"
    assert data["analysisStatus"] == "error", f"Expected analysisStatus='error' for invalid input, got '{data['analysisStatus']}'"

