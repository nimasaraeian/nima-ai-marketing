"""
Unit tests for page type detection.
"""
import unittest
from api.brain.context.page_type import detect_page_type
from api.brain.context.brand_context import PageIntent, BrandContext


class TestPageType(unittest.TestCase):
    """Test page type detection."""
    
    def test_ecommerce_product_detection(self):
        """Test ecommerce product page detection."""
        url = "https://shopify.com/products/example-product"
        page_text = "Add to cart buy now shipping returns size color quantity in stock"
        page_map = None
        intent = PageIntent(intent="product", confidence=0.7, signals={})
        brand_ctx = BrandContext(brand_maturity="growth", confidence=0.6, signals={}, analysis_mode="standard")
        
        page_type = detect_page_type(url, page_text, page_map, intent, brand_ctx)
        
        self.assertEqual(page_type.type, "ecommerce_product")
        self.assertGreater(page_type.confidence, 0.5)
        self.assertIn("ecommerce_product_url", page_type.signals)
        self.assertIn("ecommerce_keywords", page_type.signals)
    
    def test_ecommerce_checkout_detection(self):
        """Test ecommerce checkout page detection."""
        url = "https://example.com/checkout"
        page_text = "Checkout payment delivery address order summary billing"
        page_map = None
        intent = PageIntent(intent="unknown", confidence=0.5, signals={})
        brand_ctx = BrandContext(brand_maturity="growth", confidence=0.5, signals={}, analysis_mode="standard")
        
        page_type = detect_page_type(url, page_text, page_map, intent, brand_ctx)
        
        self.assertEqual(page_type.type, "ecommerce_checkout")
        self.assertGreater(page_type.confidence, 0.5)
    
    def test_saas_pricing_detection(self):
        """Test SaaS pricing page detection."""
        url = "https://example.com/pricing"
        page_text = "Pricing plans per month per user starter enterprise tier"
        page_map = None
        intent = PageIntent(intent="pricing", confidence=0.8, signals={})
        brand_ctx = BrandContext(brand_maturity="growth", confidence=0.6, signals={}, analysis_mode="standard")
        
        page_type = detect_page_type(url, page_text, page_map, intent, brand_ctx)
        
        self.assertEqual(page_type.type, "saas_pricing")
        self.assertGreater(page_type.confidence, 0.5)
        self.assertIn("pricing_intent", page_type.signals)
    
    def test_local_service_detection(self):
        """Test local service page detection."""
        url = "https://clinic.com"
        page_text = "Book appointment call now location hours clinic directions visit us"
        page_map = None
        intent = PageIntent(intent="lead_generation", confidence=0.7, signals={})
        brand_ctx = BrandContext(brand_maturity="startup", confidence=0.5, signals={}, analysis_mode="standard")
        
        page_type = detect_page_type(url, page_text, page_map, intent, brand_ctx)
        
        self.assertEqual(page_type.type, "local_service")
        self.assertGreater(page_type.confidence, 0.5)
        self.assertIn("local_keywords", page_type.signals)
    
    def test_leadgen_landing_detection(self):
        """Test lead generation landing page detection."""
        url = "https://example.com"
        page_text = "Book a call get a quote free consultation request audit contact form schedule calendly"
        page_map = None
        intent = PageIntent(intent="lead_generation", confidence=0.8, signals={})
        brand_ctx = BrandContext(brand_maturity="growth", confidence=0.5, signals={}, analysis_mode="standard")
        
        page_type = detect_page_type(url, page_text, page_map, intent, brand_ctx)
        
        self.assertEqual(page_type.type, "leadgen_landing")
        self.assertGreater(page_type.confidence, 0.5)
        self.assertIn("leadgen_keywords", page_type.signals)
    
    def test_marketplace_detection(self):
        """Test marketplace page detection."""
        url = "https://marketplace.com"
        page_text = "Listings sellers buyers categories compare offers multiple sellers"
        page_map = None
        intent = PageIntent(intent="product", confidence=0.6, signals={})
        brand_ctx = BrandContext(brand_maturity="growth", confidence=0.5, signals={}, analysis_mode="standard")
        
        page_type = detect_page_type(url, page_text, page_map, intent, brand_ctx)
        
        self.assertEqual(page_type.type, "marketplace")
        self.assertGreater(page_type.confidence, 0.5)
        self.assertIn("marketplace_keywords", page_type.signals)
    
    def test_enterprise_b2b_detection(self):
        """Test enterprise B2B page detection."""
        url = "https://enterprise.com"
        page_text = "Compliance security SOC 2 contact sales RFP enterprise"
        page_map = {
            "headlines": [{"tag": "h1", "text": "Enterprise Security"}],
            "ctas": [{"label": "Contact Sales"}]
        }
        intent = PageIntent(intent="enterprise_sales", confidence=0.8, signals={})
        brand_ctx = BrandContext(brand_maturity="enterprise", confidence=0.9, signals={}, analysis_mode="enterprise_context_aware")
        
        page_type = detect_page_type(url, page_text, page_map, intent, brand_ctx)
        
        self.assertEqual(page_type.type, "enterprise_b2b")
        self.assertGreater(page_type.confidence, 0.5)
        self.assertIn("enterprise_keywords", page_type.signals)
    
    def test_course_education_detection(self):
        """Test course/education page detection."""
        url = "https://course.com"
        page_text = "Curriculum lessons syllabus enroll certificate instructor course module"
        page_map = None
        intent = PageIntent(intent="product", confidence=0.6, signals={})
        brand_ctx = BrandContext(brand_maturity="growth", confidence=0.5, signals={}, analysis_mode="standard")
        
        page_type = detect_page_type(url, page_text, page_map, intent, brand_ctx)
        
        self.assertEqual(page_type.type, "course_or_education")
        self.assertGreater(page_type.confidence, 0.5)
        self.assertIn("course_keywords", page_type.signals)
    
    def test_content_blog_detection(self):
        """Test content/blog page detection."""
        url = "https://example.com/blog/post"
        page_text = "Subscribe to our blog"
        page_map = None
        intent = PageIntent(intent="blog", confidence=0.9, signals={})
        brand_ctx = BrandContext(brand_maturity="growth", confidence=0.5, signals={}, analysis_mode="standard")
        
        page_type = detect_page_type(url, page_text, page_map, intent, brand_ctx)
        
        self.assertEqual(page_type.type, "content_blog")
        self.assertGreater(page_type.confidence, 0.5)
        self.assertIn("blog_intent", page_type.signals)
    
    def test_app_download_detection(self):
        """Test app download page detection."""
        url = "https://app.com"
        page_text = "App Store Google Play download the app get the app mobile app"
        page_map = None
        intent = PageIntent(intent="product", confidence=0.6, signals={})
        brand_ctx = BrandContext(brand_maturity="growth", confidence=0.5, signals={}, analysis_mode="standard")
        
        page_type = detect_page_type(url, page_text, page_map, intent, brand_ctx)
        
        self.assertEqual(page_type.type, "app_download")
        self.assertGreater(page_type.confidence, 0.5)
        self.assertIn("app_keywords", page_type.signals)


if __name__ == "__main__":
    unittest.main()

