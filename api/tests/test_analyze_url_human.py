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


def test_issues_count_matches_findings():
    """
    Test that issues_count matches the actual number of issues in findings.top_issues.
    """
    payload = {
        "url": "https://example.com",
        "goal": "leads",
        "locale": "en"
    }
    
    response = client.post("/api/analyze/url-human", json=payload)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    assert data.get("analysisStatus") == "ok", "Analysis must succeed"
    
    # Get issues_count from summary
    summary = data.get("summary", {})
    issues_count = summary.get("issues_count", 0)
    
    # Get actual issues from findings
    findings = data.get("findings", {})
    top_issues = findings.get("top_issues", [])
    actual_issues = len(top_issues) if isinstance(top_issues, list) else 0
    
    # Assert they match
    assert issues_count == actual_issues, f"issues_count ({issues_count}) must equal len(findings.top_issues) ({actual_issues})"


def test_issues_count_matches_human_report():
    """
    Test that issues_count matches the number of issues listed in human_report.
    
    If human_report lists N issues (numbered 1., 2., 3., etc.), issues_count must be N.
    """
    import re
    
    payload = {
        "url": "https://example.com",
        "goal": "leads",
        "locale": "en"
    }
    
    response = client.post("/api/analyze/url-human", json=payload)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    assert data.get("analysisStatus") == "ok", "Analysis must succeed"
    
    # Get issues_count from summary
    summary = data.get("summary", {})
    issues_count = summary.get("issues_count", 0)
    
    # Get human_report
    human_report = data.get("human_report", "")
    assert isinstance(human_report, str), "human_report must be a string"
    assert len(human_report) > 0, "human_report must be non-empty"
    
    # Count numbered issues in report (pattern: "1.", "2.", "3." at start of line or after markdown)
    issue_pattern = re.compile(r'^(\d+)\.\s+\*\*', re.MULTILINE)
    report_issues = issue_pattern.findall(human_report)
    report_issues_count = len(report_issues) if report_issues else 0
    
    # Assert they match
    assert issues_count == report_issues_count, (
        f"issues_count ({issues_count}) must equal number of issues in human_report ({report_issues_count}). "
        f"Report issues found: {report_issues}"
    )


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

