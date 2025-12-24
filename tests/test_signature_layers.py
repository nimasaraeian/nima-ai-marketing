"""
Unit tests for signature layers enhancer.

Tests that build_signature_layers:
1. Returns all required keys
2. Outputs English-only content (no non-ASCII weird chars)
3. Primary CTA is not generic
4. Backward compatibility: existing keys still present
"""
import unittest
from api.brain.decision_engine.enhancers import build_signature_layers


class TestSignatureLayers(unittest.TestCase):
    """Test signature layers builder."""
    
    def test_low_trust_report(self):
        """Test with low trust issues."""
        report = {
            "findings": {
                "top_issues": [
                    {
                        "type": "trust_signal_missing",
                        "description": "No testimonials or social proof visible"
                    },
                    {
                        "type": "credibility_gap",
                        "description": "Claims exceed visible evidence"
                    }
                ],
                "issues": [],
                "quick_wins": []
            },
            "human_report": "## Verdict\nUsers hesitate because trust signals are missing.",
            "page_type": "service_landing",
            "summary": {"goal": "leads"}
        }
        
        layers = build_signature_layers(report)
        
        # Check all keys exist
        self.assertIn("decision_psychology_insight", layers)
        self.assertIn("cta_recommendations", layers)
        self.assertIn("cost_of_inaction", layers)
        self.assertIn("mindset_personas", layers)
        
        # Check psychology insight structure
        insight = layers["decision_psychology_insight"]
        self.assertIn("headline", insight)
        self.assertIn("insight", insight)
        self.assertIn("why_now", insight)
        self.assertIn("micro_risk_reducer", insight)
        
        # Check it's trust-focused (check insight field which contains trust-related content)
        insight_text = (insight["headline"] + " " + insight["insight"]).lower()
        self.assertIn("trust", insight_text or "safe" in insight_text or "risk" in insight_text)
        
        # Check CTA recommendations
        cta_rec = layers["cta_recommendations"]
        self.assertIn("primary", cta_rec)
        self.assertIn("secondary", cta_rec)
        self.assertIn("do_not_use", cta_rec)
        
        # Check primary CTA is not generic
        primary_label = cta_rec["primary"]["label"]
        self.assertNotIn("start your journey", primary_label.lower())
        self.assertNotIn("learn more", primary_label.lower())
        self.assertNotEqual("Get Started", primary_label)
        
        # Check English-only (no non-ASCII weird chars)
        self._assert_english_only(str(layers))
        
        # Check personas
        personas = layers["mindset_personas"]
        self.assertEqual(len(personas), 3)
        self.assertEqual(personas[0]["id"], "hesitant")
        self.assertEqual(personas[1]["id"], "curious")
        self.assertEqual(personas[2]["id"], "ready")
        
        # Check hesitant persona is trust-focused
        self.assertIn("trust", personas[0]["signal"].lower())
    
    def test_high_cta_competition_report(self):
        """Test with high CTA competition issues."""
        report = {
            "findings": {
                "top_issues": [
                    {
                        "type": "cta_competition",
                        "description": "Multiple CTAs competing for attention"
                    },
                    {
                        "type": "choice_paralysis",
                        "description": "Too many decision paths"
                    }
                ],
                "issues": [],
                "quick_wins": []
            },
            "human_report": "## Verdict\nUsers hesitate because too many choices cause paralysis.",
            "page_type": "saas_landing",
            "summary": {"goal": "conversions"}
        }
        
        layers = build_signature_layers(report)
        
        # Check CTA competition is detected
        insight = layers["decision_psychology_insight"]
        self.assertIn("choice", insight["headline"].lower() or insight["insight"].lower())
        
        # Check primary CTA addresses friction
        primary_label = layers["cta_recommendations"]["primary"]["label"]
        self.assertIn("friction", primary_label.lower() or layers["cta_recommendations"]["primary"]["reason"].lower())
        
        # Check ready persona addresses CTA/flow
        ready_persona = layers["mindset_personas"][2]
        self.assertIn("cta", ready_persona["signal"].lower() or ready_persona["goal"].lower())
        
        self._assert_english_only(str(layers))
    
    def test_unclear_h1_report(self):
        """Test with unclear H1 issues."""
        report = {
            "findings": {
                "top_issues": [
                    {
                        "type": "h1_unclear",
                        "description": "H1 is vague and doesn't communicate value"
                    },
                    {
                        "type": "value_proposition_unclear",
                        "description": "Core value is ambiguous"
                    }
                ],
                "issues": [],
                "quick_wins": []
            },
            "human_report": "## Verdict\nUsers hesitate because value proposition is unclear.",
            "page_type": "content_site",
            "summary": {"goal": "engagement"}
        }
        
        layers = build_signature_layers(report)
        
        # Check clarity issue is detected
        insight = layers["decision_psychology_insight"]
        self.assertIn("unclear", insight["headline"].lower() or insight["insight"].lower())
        
        # Check primary CTA addresses clarity
        primary_label = layers["cta_recommendations"]["primary"]["label"]
        self.assertIn("diagnosis", primary_label.lower() or "clarity" in primary_label.lower())
        
        # Check curious persona addresses clarity
        curious_persona = layers["mindset_personas"][1]
        self.assertIn("clarity", curious_persona["signal"].lower() or curious_persona["goal"].lower())
        
        self._assert_english_only(str(layers))
    
    def test_backward_compatibility(self):
        """Test that existing report keys are still present (backward compatibility)."""
        report = {
            "analysisStatus": "ok",
            "human_report": "Test report",
            "findings": {
                "top_issues": [],
                "issues": [],
                "quick_wins": []
            },
            "page_type": "unknown",
            "summary": {"goal": "other"}
        }
        
        layers = build_signature_layers(report)
        
        # New layers should be added, not replace existing
        # This test ensures the function doesn't modify the original report
        self.assertIn("analysisStatus", report)
        self.assertIn("human_report", report)
        self.assertIn("findings", report)
        
        # New layers should exist
        self.assertIn("decision_psychology_insight", layers)
        self.assertIn("cta_recommendations", layers)
        self.assertIn("cost_of_inaction", layers)
        self.assertIn("mindset_personas", layers)
    
    def test_cost_of_inaction_structure(self):
        """Test cost of inaction has correct structure."""
        report = {
            "findings": {
                "top_issues": [{"type": "trust", "description": "No trust signals"}],
                "issues": [],
                "quick_wins": []
            },
            "human_report": "",
            "page_type": "service",
            "summary": {"goal": "leads"}
        }
        
        layers = build_signature_layers(report)
        cost = layers["cost_of_inaction"]
        
        self.assertEqual(cost["headline"], "What This Is Costing You")
        self.assertIn("bullets", cost)
        self.assertEqual(len(cost["bullets"]), 3)  # Exactly 3 bullets
        self.assertIn("metric_hint", cost)
        
        # All bullets should be strings
        for bullet in cost["bullets"]:
            self.assertIsInstance(bullet, str)
            self.assertGreater(len(bullet), 0)
    
    def test_personas_structure(self):
        """Test personas have correct structure."""
        report = {
            "findings": {
                "top_issues": [{"type": "pricing", "description": "Pricing unclear"}],
                "issues": [],
                "quick_wins": []
            },
            "human_report": "",
            "page_type": "saas",
            "summary": {"goal": "conversions"}
        }
        
        layers = build_signature_layers(report)
        personas = layers["mindset_personas"]
        
        self.assertEqual(len(personas), 3)
        
        required_fields = ["id", "title", "signal", "goal", "best_cta", "next_step"]
        for persona in personas:
            for field in required_fields:
                self.assertIn(field, persona)
                self.assertIsInstance(persona[field], str)
                self.assertGreater(len(persona[field]), 0)
        
        # Check IDs
        self.assertEqual(personas[0]["id"], "hesitant")
        self.assertEqual(personas[1]["id"], "curious")
        self.assertEqual(personas[2]["id"], "ready")
    
    def _assert_english_only(self, text: str):
        """Assert text contains only English characters (no weird non-ASCII)."""
        # Allow common punctuation and whitespace
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?;:()[]{}\"'-")
        
        for char in text:
            if char not in allowed_chars and ord(char) > 127:
                # Check if it's a common Unicode character we might want to allow
                # (like smart quotes, em dashes, etc.)
                if ord(char) not in [8216, 8217, 8220, 8221, 8211, 8212, 8230]:
                    self.fail(f"Non-ASCII character found: {repr(char)} (U+{ord(char):04X}) in text: {text[:100]}")


if __name__ == "__main__":
    unittest.main()

