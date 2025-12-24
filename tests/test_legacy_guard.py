"""
Guard test to ensure legacy verdict phrases are NOT present in response.
"""
import unittest
from api.brain.decision_engine.human_report_builder import build_human_decision_review
from unittest.mock import AsyncMock, patch


class TestLegacyGuard(unittest.TestCase):
    """Test that legacy phrases are not present in response."""
    
    @patch('api.brain.decision_engine.human_report_builder.capture_page_artifacts')
    @patch('api.brain.decision_engine.human_report_builder.extract_page_map')
    @patch('api.brain.decision_engine.human_report_builder.run_heuristics')
    def test_no_legacy_phrases_in_response(self, mock_heuristics, mock_extract, mock_capture):
        """Test that response does NOT contain legacy phrases."""
        # Mock responses
        mock_capture.return_value = {
            "timestamp_utc": "2024-01-01T00:00:00Z",
            "screenshots": {
                "desktop": {
                    "above_the_fold_data_url": "data:image/png;base64,test",
                    "full_page_data_url": "data:image/png;base64,test",
                    "viewport": {"width": 1365, "height": 768}
                },
                "mobile": {
                    "above_the_fold_data_url": "data:image/png;base64,test",
                    "full_page_data_url": "data:image/png;base64,test",
                    "viewport": {"width": 390, "height": 844}
                }
            },
            "dom": {
                "title": "Test Page",
                "readable_text_excerpt": "Test content"
            }
        }
        
        mock_extract.return_value = {
            "headlines": [{"tag": "h1", "text": "Test"}],
            "ctas": [{"label": "Test CTA"}]
        }
        
        mock_heuristics.return_value = {
            "findings": {
                "top_issues": [],
                "quick_wins": []
            },
            "page_context": {"page_type": "unknown"},
            "summary": {"goal": "other"}
        }
        
        # Call builder
        import asyncio
        response = asyncio.run(build_human_decision_review(
            url="https://example.com",
            goal="other",
            locale="en"
        ))
        
        # Check human_report
        human_report = response.get("human_report", "").lower()
        
        # Legacy phrases that should NOT be present
        forbidden_phrases = [
            "lacks trust signals",
            "untrustworthy",
            "suggested h1",
            "suggested primary cta"
        ]
        
        found_forbidden = []
        for phrase in forbidden_phrases:
            if phrase in human_report:
                found_forbidden.append(phrase)
        
        # Also check for numbered issues (1., 2., 3.)
        import re
        numbered_issues = re.findall(r'^\d+\.\s+\*\*', human_report, re.MULTILINE)
        if numbered_issues:
            found_forbidden.append(f"numbered issues: {numbered_issues}")
        
        # Assert no forbidden phrases
        self.assertEqual(
            len(found_forbidden), 0,
            f"Legacy phrases found in human_report: {found_forbidden}. Report: {human_report[:500]}"
        )
        
        # Check debug.source
        debug = response.get("debug", {})
        self.assertEqual(debug.get("source"), "human_report_v2_only")
        
        # Check no legacy fields
        self.assertNotIn("suggested_h1", response)
        self.assertNotIn("suggested_primary_cta", response)
    
    @patch('api.brain.decision_engine.human_report_builder.capture_page_artifacts')
    @patch('api.brain.decision_engine.human_report_builder.extract_page_map')
    @patch('api.brain.decision_engine.human_report_builder.run_heuristics')
    def test_debug_source_assertion(self, mock_heuristics, mock_extract, mock_capture):
        """Test that debug.source is set correctly."""
        # Mock responses
        mock_capture.return_value = {
            "timestamp_utc": "2024-01-01T00:00:00Z",
            "screenshots": {
                "desktop": {"above_the_fold_data_url": "data:image/png;base64,test", "full_page_data_url": "data:image/png;base64,test", "viewport": {"width": 1365, "height": 768}},
                "mobile": {"above_the_fold_data_url": "data:image/png;base64,test", "full_page_data_url": "data:image/png;base64,test", "viewport": {"width": 390, "height": 844}}
            },
            "dom": {"title": "Test", "readable_text_excerpt": "Test"}
        }
        mock_extract.return_value = {"headlines": [], "ctas": []}
        mock_heuristics.return_value = {
            "findings": {"top_issues": [], "quick_wins": []},
            "page_context": {"page_type": "unknown"},
            "summary": {"goal": "other"}
        }
        
        import asyncio
        response = asyncio.run(build_human_decision_review(
            url="https://example.com",
            goal="other",
            locale="en"
        ))
        
        debug = response.get("debug", {})
        self.assertEqual(debug.get("source"), "human_report_v2_only")
        self.assertEqual(debug.get("pipeline_version"), "human_report_v2")


if __name__ == "__main__":
    unittest.main()

