"""
Unit tests for page-type-specific templates.
"""
import unittest
from api.brain.decision_engine.templates_by_type import apply_page_type_templates


class TestTemplatesByType(unittest.TestCase):
    """Test page-type-specific templates."""
    
    def test_ecommerce_product_templates(self):
        """Test ecommerce product page templates."""
        response = {
            "cta_recommendations": {
                "primary": {"label": "Learn More", "reason": "Generic"},
                "secondary": [],
                "do_not_use": []
            },
            "mindset_personas": [
                {"id": "hesitant", "title": "Hesitant Visitor"},
                {"id": "curious", "title": "Curious Evaluator"},
                {"id": "ready", "title": "Ready-to-Act Buyer"}
            ],
            "decision_psychology_insight": {
                "headline": "Generic Insight",
                "insight": "Generic insight text"
            }
        }
        
        ctx = {
            "page_type": {
                "type": "ecommerce_product",
                "confidence": 0.8
            }
        }
        
        result = apply_page_type_templates(response, ctx)
        
        # Check primary CTA is transactional
        primary_cta = result["cta_recommendations"]["primary"]["label"]
        self.assertIn(primary_cta.lower(), ["add to cart", "buy now", "choose size & add to cart"])
        
        # Check personas are ecommerce-specific
        hesitant = next((p for p in result["mindset_personas"] if p["id"] == "hesitant"), None)
        self.assertIsNotNone(hesitant)
        self.assertIn("risk", hesitant["title"].lower() or hesitant["signal"].lower())
        
        # Check insight is ecommerce-focused
        insight = result["decision_psychology_insight"]
        self.assertIn("product", insight["headline"].lower() or insight["insight"].lower())
    
    def test_leadgen_landing_templates(self):
        """Test lead generation landing page templates."""
        response = {
            "cta_recommendations": {
                "primary": {"label": "Get Started", "reason": "Generic"},
                "secondary": [],
                "do_not_use": []
            },
            "decision_psychology_insight": {
                "headline": "Generic",
                "insight": "Generic"
            }
        }
        
        ctx = {
            "page_type": {
                "type": "leadgen_landing",
                "confidence": 0.8
            }
        }
        
        result = apply_page_type_templates(response, ctx)
        
        # Check primary CTA is leadgen-specific
        primary_cta = result["cta_recommendations"]["primary"]["label"]
        self.assertIn(primary_cta.lower(), ["book a call", "get a quote", "schedule appointment"])
        
        # Check insight mentions credibility/risk reversal
        insight = result["decision_psychology_insight"]
        self.assertTrue(
            "credibility" in insight["insight"].lower() or
            "risk reversal" in insight["insight"].lower()
        )
    
    def test_enterprise_b2b_templates(self):
        """Test enterprise B2B templates."""
        response = {
            "cta_recommendations": {
                "primary": {"label": "Get Started", "reason": "Generic"},
                "secondary": [],
                "do_not_use": []
            },
            "decision_psychology_insight": {
                "headline": "Trust Signals Missing",
                "insight": "Users lack trust signals"
            }
        }
        
        ctx = {
            "page_type": {
                "type": "enterprise_b2b",
                "confidence": 0.9
            },
            "page_intent": {
                "intent": "pricing"
            }
        }
        
        result = apply_page_type_templates(response, ctx)
        
        # Check primary CTA is enterprise-appropriate
        primary_cta = result["cta_recommendations"]["primary"]["label"]
        self.assertIn(primary_cta.lower(), ["talk to sales", "request demo", "see security & compliance"])
        
        # Check no naive trust claims
        insight = result["decision_psychology_insight"]
        headline_lower = insight["headline"].lower()
        self.assertFalse(
            "trust" in headline_lower and "missing" in headline_lower
        )
    
    def test_saas_pricing_templates(self):
        """Test SaaS pricing page templates."""
        # Enterprise SaaS
        response_enterprise = {
            "cta_recommendations": {
                "primary": {"label": "Get Started", "reason": "Generic"},
                "secondary": []
            }
        }
        
        ctx_enterprise = {
            "page_type": {"type": "saas_pricing", "confidence": 0.9},
            "brand_context": {"brand_maturity": "enterprise"}
        }
        
        result_enterprise = apply_page_type_templates(response_enterprise, ctx_enterprise)
        primary_cta_enterprise = result_enterprise["cta_recommendations"]["primary"]["label"]
        self.assertIn("sales", primary_cta_enterprise.lower())
        
        # Growth SaaS
        response_growth = {
            "cta_recommendations": {
                "primary": {"label": "Get Started", "reason": "Generic"},
                "secondary": []
            }
        }
        
        ctx_growth = {
            "page_type": {"type": "saas_pricing", "confidence": 0.9},
            "brand_context": {"brand_maturity": "growth"}
        }
        
        result_growth = apply_page_type_templates(response_growth, ctx_growth)
        primary_cta_growth = result_growth["cta_recommendations"]["primary"]["label"]
        self.assertIn("trial", primary_cta_growth.lower())
    
    def test_unknown_page_type_no_change(self):
        """Test that unknown page type doesn't change response."""
        response = {
            "cta_recommendations": {
                "primary": {"label": "Original", "reason": "Original"}
            }
        }
        
        ctx = {
            "page_type": {
                "type": "unknown",
                "confidence": 0.0
            }
        }
        
        result = apply_page_type_templates(response, ctx)
        
        # Should be unchanged
        self.assertEqual(result["cta_recommendations"]["primary"]["label"], "Original")
    
    def test_content_blog_templates(self):
        """Test content/blog page templates."""
        response = {
            "cta_recommendations": {
                "primary": {"label": "Get Started", "reason": "Generic"},
                "secondary": []
            }
        }
        
        ctx = {
            "page_type": {
                "type": "content_blog",
                "confidence": 0.8
            }
        }
        
        result = apply_page_type_templates(response, ctx)
        
        primary_cta = result["cta_recommendations"]["primary"]["label"]
        self.assertEqual(primary_cta.lower(), "subscribe")


if __name__ == "__main__":
    unittest.main()




