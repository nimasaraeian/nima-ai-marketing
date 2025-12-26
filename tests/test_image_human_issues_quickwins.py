"""
Regression test for /api/analyze/image-human endpoint.

Ensures that 'issues' and 'quick_wins' keys are ALWAYS present in the response,
even if empty, to track where they might be lost in the pipeline.
"""
import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


@pytest.fixture
def sample_image_path():
    """Get path to a sample image for testing."""
    # Try to find any image in the project
    possible_paths = [
        "api/artifacts/atf_desktop_1766482842.png",
        "test_image.jpg",
        "test.jpg",
        "shot.png"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # If no image found, skip the test
    pytest.skip("No sample image found for testing")


def test_image_human_always_includes_issues_and_quick_wins(sample_image_path):
    """
    Regression test: POST an image to /api/analyze/image-human and assert
    keys "issues" and "quick_wins" exist (even if empty).
    """
    image_path = Path(sample_image_path)
    
    with open(image_path, "rb") as f:
        files = {"image": (image_path.name, f, "image/png")}
        data = {"goal": "leads"}
        
        response = client.post("/api/analyze/image-human", files=files, data=data)
    
    # Assert successful response
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    result = response.json()
    
    # CRITICAL: Assert that 'issues' key exists (even if empty list)
    assert "issues" in result, (
        f"Response missing 'issues' key. Available keys: {list(result.keys())}"
    )
    assert isinstance(result["issues"], list), (
        f"'issues' must be a list, got {type(result['issues'])}"
    )
    
    # CRITICAL: Assert that 'quick_wins' key exists (even if empty list)
    assert "quick_wins" in result, (
        f"Response missing 'quick_wins' key. Available keys: {list(result.keys())}"
    )
    assert isinstance(result["quick_wins"], list), (
        f"'quick_wins' must be a list, got {type(result['quick_wins'])}"
    )
    
    # Assert issues_count exists and matches length
    assert "issues_count" in result, "Response missing 'issues_count' key"
    assert isinstance(result["issues_count"], int), "'issues_count' must be an integer"
    assert result["issues_count"] == len(result["issues"]), (
        f"issues_count ({result['issues_count']}) doesn't match issues length ({len(result['issues'])})"
    )
    
    # Assert summary has issues_count and quick_wins_count
    assert "summary" in result, "Response missing 'summary' key"
    summary = result["summary"]
    assert isinstance(summary, dict), "'summary' must be a dictionary"
    
    assert "issues_count" in summary, "Summary missing 'issues_count' key"
    assert summary["issues_count"] == result["issues_count"], (
        f"summary.issues_count ({summary['issues_count']}) doesn't match top-level issues_count ({result['issues_count']})"
    )
    
    assert "quick_wins_count" in summary, "Summary missing 'quick_wins_count' key"
    assert isinstance(summary["quick_wins_count"], int), "'quick_wins_count' must be an integer"
    assert summary["quick_wins_count"] == len(result["quick_wins"]), (
        f"summary.quick_wins_count ({summary['quick_wins_count']}) doesn't match quick_wins length ({len(result['quick_wins'])})"
    )
    
    # Assert debug snapshots exist
    assert "debug" in result, "Response missing 'debug' key"
    debug = result["debug"]
    assert isinstance(debug, dict), "'debug' must be a dictionary"
    
    # Check for after_heuristics snapshot
    assert "after_heuristics" in debug, "Debug missing 'after_heuristics' snapshot"
    after_heuristics = debug["after_heuristics"]
    assert isinstance(after_heuristics, dict), "'after_heuristics' must be a dictionary"
    assert "issues_len" in after_heuristics, "after_heuristics missing 'issues_len'"
    assert "quick_wins_len" in after_heuristics, "after_heuristics missing 'quick_wins_len'"
    
    # Check for after_finalize snapshot
    assert "after_finalize_keys" in debug, "Debug missing 'after_finalize_keys' snapshot"
    assert "after_finalize_counts" in debug, "Debug missing 'after_finalize_counts' snapshot"
    after_finalize_counts = debug["after_finalize_counts"]
    assert isinstance(after_finalize_counts, dict), "'after_finalize_counts' must be a dictionary"
    assert "has_issues_key" in after_finalize_counts, "after_finalize_counts missing 'has_issues_key'"
    assert "has_quick_wins_key" in after_finalize_counts, "after_finalize_counts missing 'has_quick_wins_key'"
    
    # Log debug info for manual inspection
    print(f"\n=== Debug Snapshot Analysis ===")
    print(f"After heuristics - issues_len: {after_heuristics.get('issues_len')}, quick_wins_len: {after_heuristics.get('quick_wins_len')}")
    print(f"After finalize - has_issues_key: {after_finalize_counts.get('has_issues_key')}, has_quick_wins_key: {after_finalize_counts.get('has_quick_wins_key')}")
    print(f"Final response - issues_count: {result['issues_count']}, quick_wins_count: {summary['quick_wins_count']}")
    print(f"Final response - issues length: {len(result['issues'])}, quick_wins length: {len(result['quick_wins'])}")


def test_image_human_debug_snapshots_track_data_flow(sample_image_path):
    """
    Test that debug snapshots correctly track the flow of issues and quick_wins
    through the pipeline.
    """
    image_path = Path(sample_image_path)
    
    with open(image_path, "rb") as f:
        files = {"image": (image_path.name, f, "image/png")}
        data = {"goal": "leads"}
        
        response = client.post("/api/analyze/image-human", files=files, data=data)
    
    assert response.status_code == 200
    result = response.json()
    debug = result.get("debug", {})
    
    # Get snapshot data
    after_heuristics = debug.get("after_heuristics", {})
    after_finalize_counts = debug.get("after_finalize_counts", {})
    
    # Verify data flow tracking
    issues_after_heuristics = after_heuristics.get("issues_len", 0)
    quick_wins_after_heuristics = after_heuristics.get("quick_wins_len", 0)
    
    final_issues_count = result.get("issues_count", 0)
    final_quick_wins_count = result.get("summary", {}).get("quick_wins_count", 0)
    
    # Log the flow for debugging
    print(f"\n=== Data Flow Tracking ===")
    print(f"Heuristics → Issues: {issues_after_heuristics}, Quick Wins: {quick_wins_after_heuristics}")
    print(f"Final → Issues: {final_issues_count}, Quick Wins: {final_quick_wins_count}")
    
    # The final counts should match what was found in heuristics (or be limited to top 3 for issues)
    # Issues might be limited to top 3, so final should be <= heuristics
    assert final_issues_count <= issues_after_heuristics, (
        f"Final issues_count ({final_issues_count}) should be <= heuristics issues_len ({issues_after_heuristics})"
    )
    
    # Quick wins should match (no limiting applied)
    assert final_quick_wins_count == quick_wins_after_heuristics, (
        f"Final quick_wins_count ({final_quick_wins_count}) should match heuristics quick_wins_len ({quick_wins_after_heuristics})"
    )

