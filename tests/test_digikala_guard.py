"""
Tests for hard guards against naive trust language for large ecommerce brands.
"""
import unittest
from api.brain.decision_engine.contextualizer import sanitize_text, contextualize_verdict


class TestDigikalaGuard(unittest.TestCase):
    """Test that forbidden trust phrases are removed for large ecommerce brands."""
    
    def test_sanitize_removes_forbidden_phrases(self):
        """Test that sanitize_text removes forbidden phrases."""
        ctx = {
            "brand_context": {"brand_maturity": "enterprise"},
            "page_type": {"type": "ecommerce_product"}
        }
        
        # Test text with forbidden phrases
        text = "Users hesitate because the page feels untrustworthy and lacks trust signals. It feels risky and no trust is present."
        
        sanitized = sanitize_text(text, ctx)
        
        # Assert forbidden phrases are removed
        self.assertNotIn("untrustworthy", sanitized.lower())
        self.assertNotIn("lacks trust signals", sanitized.lower())
        self.assertNotIn("feels risky", sanitized.lower())
        self.assertNotIn("no trust", sanitized.lower())
    
    def test_sanitize_preserves_text_for_startup(self):
        """Test that sanitize_text does NOT remove phrases for startup brands."""
        ctx = {
            "brand_context": {"brand_maturity": "startup"},
            "page_type": {"type": "unknown"}
        }
        
        text = "Users hesitate because the page feels untrustworthy."
        
        sanitized = sanitize_text(text, ctx)
        
        # Should preserve text for startup brands
        self.assertIn("untrustworthy", sanitized.lower())
    
    def test_contextualize_removes_forbidden_phrases(self):
        """Test that contextualize_verdict removes forbidden phrases."""
        payload = {
            "human_report": "## Verdict\nUsers hesitate because the page lacks trust signals and feels untrustworthy.",
            "decision_psychology_insight": {
                "headline": "Trust Signals Missing",
                "insight": "Users see capability but lack trust signals needed to commit.",
                "why_now": "Trust debt accumulates silently.",
                "micro_risk_reducer": "Add trust signals above the fold."
            },
            "mindset_personas": [
                {
                    "id": "hesitant",
                    "title": "Hesitant Visitor",
                    "signal": "Trust/risk dominant - lacks trust signals",
                    "goal": "Reduce perceived risk",
                    "best_cta": "Get Started",
                    "next_step": "Add trust signals"
                }
            ]
        }
        
        ctx = {
            "brand_context": {
                "brand_maturity": "enterprise",
                "analysis_mode": "enterprise_context_aware"
            },
            "page_intent": {"intent": "pricing"},
            "page_type": {"type": "ecommerce_product"}
        }
        
        result = contextualize_verdict(payload, ctx)
        
        # Check human_report
        human_report = result.get("human_report", "")
        self.assertNotIn("lacks trust signals", human_report.lower())
        self.assertNotIn("untrustworthy", human_report.lower())
        
        # Check insight
        insight = result.get("decision_psychology_insight", {})
        insight_text = " ".join([
            insight.get("headline", ""),
            insight.get("insight", ""),
            insight.get("why_now", ""),
            insight.get("micro_risk_reducer", "")
        ]).lower()
        self.assertNotIn("trust signals missing", insight_text)
        self.assertNotIn("lacks trust signals", insight_text)
        
        # Check personas
        personas = result.get("mindset_personas", [])
        for persona in personas:
            persona_text = " ".join([
                persona.get("title", ""),
                persona.get("signal", ""),
                persona.get("goal", ""),
                persona.get("next_step", "")
            ]).lower()
            self.assertNotIn("lacks trust signals", persona_text)
            self.assertNotIn("untrustworthy", persona_text)
    
    def test_ecommerce_product_gets_sanitized(self):
        """Test that ecommerce_product pages get sanitized even if not enterprise."""
        ctx = {
            "brand_context": {"brand_maturity": "growth"},
            "page_type": {"type": "ecommerce_product"}
        }
        
        text = "Users hesitate because the page lacks trust signals."
        
        sanitized = sanitize_text(text, ctx)
        
        # Should be sanitized for ecommerce
        self.assertNotIn("lacks trust signals", sanitized.lower())


if __name__ == "__main__":
    unittest.main()




