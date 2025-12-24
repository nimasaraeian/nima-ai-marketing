"""
Tests for response schema stability - ensure required keys always exist.
"""
import unittest
from api.brain.decision_engine.human_report_builder import build_human_decision_review
from unittest.mock import AsyncMock, patch, MagicMock


class TestResponseSchemaStability(unittest.TestCase):
    """Test that response schema is stable and all required keys exist."""
    
    @patch('api.brain.decision_engine.human_report_builder.capture_page_artifacts')
    @patch('api.brain.decision_engine.human_report_builder.extract_page_map')
    @patch('api.brain.decision_engine.human_report_builder.run_heuristics')
    @patch('api.brain.decision_engine.human_report_builder.render_human_report')
    def test_required_keys_always_exist(self, mock_render, mock_heuristics, mock_extract, mock_capture):
        """Test that all required keys always exist in response."""
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
        
        mock_render.return_value = "## Verdict\nTest report"
        
        # Call builder (use asyncio.run for sync test)
        import asyncio
        response = asyncio.run(build_human_decision_review(
            url="https://example.com",
            goal="other",
            locale="en"
        ))
        
        # Assert all required keys exist
        required_keys = [
            "brand_context",
            "page_intent",
            "page_type",
            "decision_psychology_insight",
            "cta_recommendations",
            "cost_of_inaction",
            "mindset_personas",
            "debug"
        ]
        
        for key in required_keys:
            self.assertIn(key, response, f"Required key '{key}' missing from response")
        
        # Assert debug structure
        debug = response.get("debug", {})
        self.assertEqual(debug.get("pipeline_version"), "human_report_v2")
        self.assertIn("signature_layers", debug.get("steps", []))
        
        # Assert signature layers structure
        insight = response.get("decision_psychology_insight", {})
        self.assertIn("headline", insight)
        self.assertIn("insight", insight)
        self.assertIn("why_now", insight)
        self.assertIn("micro_risk_reducer", insight)
        
        cta_rec = response.get("cta_recommendations", {})
        self.assertIn("primary", cta_rec)
        self.assertIn("secondary", cta_rec)
        self.assertIn("do_not_use", cta_rec)
        
        cost = response.get("cost_of_inaction", {})
        self.assertIn("headline", cost)
        self.assertIn("bullets", cost)
        self.assertEqual(len(cost.get("bullets", [])), 3)
        
        personas = response.get("mindset_personas", [])
        self.assertEqual(len(personas), 3)
        self.assertEqual(personas[0]["id"], "hesitant")
        self.assertEqual(personas[1]["id"], "curious")
        self.assertEqual(personas[2]["id"], "ready")
    
    @patch('api.brain.decision_engine.human_report_builder.capture_page_artifacts')
    @patch('api.brain.decision_engine.human_report_builder.extract_page_map')
    @patch('api.brain.decision_engine.human_report_builder.run_heuristics')
    @patch('api.brain.decision_engine.human_report_builder.render_human_report')
    def test_fallback_response_has_all_keys(self, mock_render, mock_heuristics, mock_extract, mock_capture):
        """Test that fallback response (on error) has all required keys."""
        # Mock to raise exception
        mock_capture.side_effect = Exception("Test error")
        
        # Call builder (should return fallback)
        import asyncio
        response = asyncio.run(build_human_decision_review(
            url="https://example.com",
            goal="other",
            locale="en"
        ))
        
        # Even on error, all keys should exist
        required_keys = [
            "brand_context",
            "page_intent",
            "page_type",
            "decision_psychology_insight",
            "cta_recommendations",
            "cost_of_inaction",
            "mindset_personas",
            "debug"
        ]
        
        for key in required_keys:
            self.assertIn(key, response, f"Required key '{key}' missing from fallback response")
        
        # Debug should show error
        debug = response.get("debug", {})
        self.assertGreater(len(debug.get("errors", [])), 0)


if __name__ == "__main__":
    import asyncio
    unittest.main()

