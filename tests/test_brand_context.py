"""
Unit tests for brand context and page intent detection.
"""
import unittest
from api.brain.context.brand_context import (
    normalize_domain,
    detect_page_intent,
    detect_brand_context,
    build_context,
    KNOWN_ENTERPRISE_DOMAINS
)


class TestBrandContext(unittest.TestCase):
    """Test brand context detection."""
    
    def test_normalize_domain(self):
        """Test domain normalization."""
        self.assertEqual(normalize_domain("https://www.stripe.com/pricing"), "stripe.com")
        self.assertEqual(normalize_domain("https://stripe.com/pricing"), "stripe.com")
        self.assertEqual(normalize_domain("http://WWW.EXAMPLE.COM"), "example.com")
        self.assertEqual(normalize_domain("notion.so"), "notion.so")
    
    def test_detect_intent_pricing(self):
        """Test pricing page intent detection."""
        url = "https://stripe.com/pricing"
        page_text = "Pricing plans per month per user starter enterprise tier subscription"
        page_map = None
        
        intent = detect_page_intent(page_text, page_map, url)
        
        self.assertEqual(intent.intent, "pricing")
        self.assertGreater(intent.confidence, 0.5)
        self.assertIn("pricing_url", intent.signals)
    
    def test_detect_intent_docs(self):
        """Test docs page intent detection."""
        url = "https://stripe.com/docs/api"
        page_text = "API documentation developers reference"
        page_map = None
        
        intent = detect_page_intent(page_text, page_map, url)
        
        self.assertEqual(intent.intent, "docs")
        self.assertGreater(intent.confidence, 0.5)
    
    def test_detect_intent_blog(self):
        """Test blog page intent detection."""
        url = "https://example.com/blog/post"
        page_text = "Subscribe to our blog"
        page_map = None
        
        intent = detect_page_intent(page_text, page_map, url)
        
        self.assertEqual(intent.intent, "blog")
        self.assertGreater(intent.confidence, 0.5)
    
    def test_detect_intent_enterprise_sales(self):
        """Test enterprise sales intent detection."""
        url = "https://example.com/enterprise"
        page_text = "Contact sales talk to sales request a demo enterprise"
        page_map = {
            "ctas": [
                {"label": "Contact Sales", "text": "Contact Sales"}
            ]
        }
        
        intent = detect_page_intent(page_text, page_map, url)
        
        self.assertEqual(intent.intent, "enterprise_sales")
        self.assertGreater(intent.confidence, 0.4)
    
    def test_enterprise_mode_stripe(self):
        """Test that stripe.com is detected as enterprise."""
        url = "https://stripe.com/pricing"
        page_text = "Stripe pricing plans enterprise compliance security"
        page_map = {
            "headlines": [
                {"tag": "h1", "text": "Stripe Pricing"}
            ]
        }
        
        intent = detect_page_intent(page_text, page_map, url)
        brand_ctx = detect_brand_context(url, page_text, page_map, intent)
        
        self.assertEqual(brand_ctx.brand_maturity, "enterprise")
        self.assertGreater(brand_ctx.confidence, 0.5)
        self.assertEqual(brand_ctx.analysis_mode, "enterprise_context_aware")
        self.assertIn("known_enterprise_domain", brand_ctx.signals)
    
    def test_enterprise_mode_notion(self):
        """Test that notion.so is detected as enterprise."""
        url = "https://notion.so/pricing"
        page_text = "Notion pricing"
        page_map = None
        
        intent = detect_page_intent(page_text, page_map, url)
        brand_ctx = detect_brand_context(url, page_text, page_map, intent)
        
        self.assertEqual(brand_ctx.brand_maturity, "enterprise")
        self.assertEqual(brand_ctx.analysis_mode, "enterprise_context_aware")
    
    def test_build_context(self):
        """Test complete context building."""
        url = "https://stripe.com/pricing"
        page_text = "Stripe pricing plans per month"
        page_map = {
            "headlines": [{"tag": "h1", "text": "Stripe Pricing"}]
        }
        
        ctx = build_context(url, page_text, page_map)
        
        self.assertIn("brand_context", ctx)
        self.assertIn("page_intent", ctx)
        self.assertEqual(ctx["brand_context"]["brand_maturity"], "enterprise")
        self.assertEqual(ctx["page_intent"]["intent"], "pricing")
        self.assertEqual(ctx["brand_context"]["analysis_mode"], "enterprise_context_aware")
    
    def test_startup_detection(self):
        """Test startup brand detection."""
        url = "https://personalbrand.com"
        page_text = "Work with me personal brand freelance consultant"
        page_map = {
            "ctas": [{"label": "Contact"}]
        }
        
        intent = detect_page_intent(page_text, page_map, url)
        brand_ctx = detect_brand_context(url, page_text, page_map, intent)
        
        # Should detect startup indicators
        self.assertIn("startup_indicators", brand_ctx.signals)
    
    def test_growth_detection(self):
        """Test growth brand detection."""
        url = "https://example.com"
        page_text = "Pricing tier plan case studies customers testimonials comparison"
        page_map = None
        
        intent = detect_page_intent(page_text, page_map, url)
        brand_ctx = detect_brand_context(url, page_text, page_map, intent)
        
        # Should have growth indicators
        self.assertIn("growth_indicators", brand_ctx.signals or {})


if __name__ == "__main__":
    unittest.main()




