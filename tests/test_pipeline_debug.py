"""
Tests for pipeline debug diagnostics.
"""
import unittest
from api.brain.decision_engine.human_report_builder import build_human_decision_review
from unittest.mock import AsyncMock, patch


class TestPipelineDebug(unittest.TestCase):
    """Test that debug diagnostics are correctly included."""
    
    @patch('api.brain.decision_engine.human_report_builder.capture_page_artifacts')
    @patch('api.brain.decision_engine.human_report_builder.extract_page_map')
    @patch('api.brain.decision_engine.human_report_builder.run_heuristics')
    def test_debug_pipeline_version(self, mock_heuristics, mock_extract, mock_capture):
        """Test that debug.pipeline_version is correct."""
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
        self.assertEqual(debug.get("pipeline_version"), "human_report_v2")
    
    @patch('api.brain.decision_engine.human_report_builder.capture_page_artifacts')
    @patch('api.brain.decision_engine.human_report_builder.extract_page_map')
    @patch('api.brain.decision_engine.human_report_builder.run_heuristics')
    def test_debug_steps_include_signature_layers(self, mock_heuristics, mock_extract, mock_capture):
        """Test that debug.steps includes signature_layers."""
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
        steps = debug.get("steps", [])
        self.assertIn("signature_layers", steps)
        self.assertIn("context", steps)
        self.assertIn("contextualize", steps)
        self.assertIn("type_templates", steps)
    
    @patch('api.brain.decision_engine.human_report_builder.capture_page_artifacts')
    @patch('api.brain.decision_engine.human_report_builder.extract_page_map')
    @patch('api.brain.decision_engine.human_report_builder.run_heuristics')
    def test_debug_includes_context_info(self, mock_heuristics, mock_extract, mock_capture):
        """Test that debug includes context information."""
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
        self.assertIn("analysis_mode", debug)
        self.assertIn("brand_maturity", debug)
        self.assertIn("page_intent", debug)
        self.assertIn("page_type", debug)
        self.assertIn("errors", debug)


if __name__ == "__main__":
    import asyncio
    unittest.main()

