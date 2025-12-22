"""
Unit/integration tests for /api/analyze/url-human endpoints.
"""
import pytest
import requests
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


def test_screenshot_urls_accessible():
    """
    Integration test: Verify screenshot URLs are actually accessible.
    
    This test:
    1. Calls /api/analyze/url-human
    2. Extracts screenshot URLs from response
    3. Fetches both screenshot URLs
    4. Asserts HTTP 200 for both
    """
    payload = {
        "url": "https://example.com",
        "goal": "leads",
        "locale": "en"
    }
    
    # Step 1: Call the analysis endpoint
    response = client.post("/api/analyze/url-human", json=payload)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    assert data.get("analysisStatus") == "ok", "Analysis must succeed"
    
    # Step 2: Extract screenshot URLs
    screenshots = data.get("screenshots", {})
    atf_url = screenshots.get("above_the_fold")
    full_url = screenshots.get("full_page")
    
    assert atf_url is not None, "above_the_fold URL must be present"
    assert full_url is not None, "full_page URL must be present"
    
    # Step 3 & 4: Fetch both URLs and assert HTTP 200
    # Note: In test environment, we need to use the test client's base URL
    # For production, these would be absolute URLs
    
    # Extract just the path from the URL for local testing
    if atf_url.startswith("http"):
        # Production URL - would need actual HTTP request
        # For now, we'll test the path directly
        atf_path = "/" + "/".join(atf_url.split("/")[-2:])  # Extract /api/artifacts/filename
    else:
        atf_path = atf_url
    
    if full_url.startswith("http"):
        full_path = "/" + "/".join(full_url.split("/")[-2:])
    else:
        full_path = full_url
    
    # Fetch screenshots using test client
    atf_response = client.get(atf_path)
    assert atf_response.status_code == 200, f"ATF screenshot must be accessible. Got {atf_response.status_code} for {atf_path}"
    assert atf_response.headers.get("content-type") == "image/png", "ATF must be PNG image"
    assert len(atf_response.content) > 0, "ATF screenshot must have content"
    
    full_response = client.get(full_path)
    assert full_response.status_code == 200, f"Full page screenshot must be accessible. Got {full_response.status_code} for {full_path}"
    assert full_response.headers.get("content-type") == "image/png", "Full page must be PNG image"
    assert len(full_response.content) > 0, "Full page screenshot must have content"

