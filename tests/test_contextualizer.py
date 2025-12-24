"""
Unit tests for contextualizer - enterprise context-aware reframing.
"""
import unittest
from api.brain.decision_engine.contextualizer import contextualize_verdict


class TestContextualizer(unittest.TestCase):
    """Test contextualizer reframing."""
    
    def test_enterprise_pricing_contextualization(self):
        """Test that enterprise pricing pages get contextualized verdicts."""
        payload = {
            "human_report": "## Verdict\nUsers hesitate because trust signals are missing and there is no clear CTA.",
            "decision_psychology_insight": {
                "headline": "Trust Signals Missing",
                "insight": "Users see capability but lack trust signals needed to commit.",
                "why_now": "Trust debt accumulates silently.",
                "micro_risk_reducer": "Add trust signals above the fold."
            },
            "cta_recommendations": {
                "primary": {
                    "label": "Get Started",
                    "reason": "Generic CTA"
                },
                "secondary": [],
                "do_not_use": []
            },
            "mindset_personas": [
                {
                    "id": "hesitant",
                    "title": "Hesitant Visitor",
                    "signal": "Trust/risk dominant",
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
            "page_intent": {
                "intent": "pricing"
            }
        }
        
        result = contextualize_verdict(payload, ctx)
        
        # Check context note is added
        self.assertIn("context_note", result)
        self.assertEqual(result["context_note"]["headline"], "Context Note")
        
        # Check naive trust claim is removed/reframed
        human_report = result["human_report"]
        self.assertNotIn("trust signals are missing", human_report.lower())
        self.assertNotIn("no trust signals", human_report.lower())
        
        # Check verdict mentions informed buyers or first-time
        self.assertTrue(
            "informed" in human_report.lower() or 
            "first-time" in human_report.lower() or 
            "price-sensitive" in human_report.lower()
        )
        
        # Check CTA is friction-diagnostic, not generic
        primary_cta = result["cta_recommendations"]["primary"]["label"]
        self.assertNotIn("get started", primary_cta.lower())
        self.assertNotIn("start your journey", primary_cta.lower())
        self.assertNotIn("learn more", primary_cta.lower())
        
        # Check insight is reframed
        insight = result["decision_psychology_insight"]
        self.assertNotIn("trust signals missing", insight["headline"].lower())
        self.assertIn("next-step", insight["headline"].lower() or insight["insight"].lower())
        
        # Check personas are reframed
        hesitant_persona = next((p for p in result["mindset_personas"] if p["id"] == "hesitant"), None)
        self.assertIsNotNone(hesitant_persona)
        self.assertIn("first-time", hesitant_persona["title"].lower() or hesitant_persona["signal"].lower())
    
    def test_standard_mode_no_change(self):
        """Test that standard mode doesn't change payload."""
        payload = {
            "human_report": "## Verdict\nUsers hesitate because trust signals are missing.",
            "decision_psychology_insight": {
                "headline": "Trust Signals Missing",
                "insight": "Users lack trust signals."
            }
        }
        
        ctx = {
            "brand_context": {
                "brand_maturity": "growth",
                "analysis_mode": "standard"
            },
            "page_intent": {
                "intent": "product"
            }
        }
        
        result = contextualize_verdict(payload, ctx)
        
        # Should be unchanged (no context note, no reframing)
        self.assertNotIn("context_note", result)
        self.assertEqual(result["human_report"], payload["human_report"])
    
    def test_docs_intent_reframing(self):
        """Test that docs pages get appropriate reframing."""
        payload = {
            "decision_psychology_insight": {
                "headline": "Missing CTA",
                "insight": "No clear call to action."
            }
        }
        
        ctx = {
            "brand_context": {
                "brand_maturity": "enterprise",
                "analysis_mode": "enterprise_context_aware"
            },
            "page_intent": {
                "intent": "docs"
            }
        }
        
        result = contextualize_verdict(payload, ctx)
        
        insight = result["decision_psychology_insight"]
        self.assertIn("navigation", insight["headline"].lower() or insight["insight"].lower())
        self.assertIn("clarity", insight["insight"].lower() or insight["headline"].lower())
    
    def test_enterprise_cta_reframing(self):
        """Test that enterprise pages get friction-diagnostic CTAs."""
        payload = {
            "cta_recommendations": {
                "primary": {
                    "label": "Get Started",
                    "reason": "Generic"
                },
                "secondary": [],
                "do_not_use": []
            }
        }
        
        ctx = {
            "brand_context": {
                "brand_maturity": "enterprise",
                "analysis_mode": "enterprise_context_aware"
            },
            "page_intent": {
                "intent": "product"
            }
        }
        
        result = contextualize_verdict(payload, ctx)
        
        primary_cta = result["cta_recommendations"]["primary"]["label"]
        self.assertNotIn("get started", primary_cta.lower())
        self.assertIn("hesitate", primary_cta.lower() or "friction" in primary_cta.lower())
    
    def test_pricing_secondary_ctas(self):
        """Test that pricing pages get appropriate secondary CTAs."""
        payload = {
            "cta_recommendations": {
                "primary": {"label": "Test", "reason": "Test"},
                "secondary": [],
                "do_not_use": []
            }
        }
        
        ctx = {
            "brand_context": {
                "brand_maturity": "enterprise",
                "analysis_mode": "enterprise_context_aware"
            },
            "page_intent": {
                "intent": "pricing"
            }
        }
        
        result = contextualize_verdict(payload, ctx)
        
        secondary = result["cta_recommendations"]["secondary"]
        self.assertGreater(len(secondary), 0)
        # Should have pricing-specific secondaries
        secondary_labels = [s["label"].lower() for s in secondary]
        self.assertTrue(
            any("plan" in label or "compare" in label for label in secondary_labels)
        )


if __name__ == "__main__":
    unittest.main()

