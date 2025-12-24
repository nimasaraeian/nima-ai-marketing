"""
Page Type Detection - Business Model/Category Classification

Detects landing page type (ecommerce, SaaS, marketplace, etc.) to enable
context-aware recommendations.
"""
from dataclasses import dataclass
from typing import Literal, Dict, Any, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


@dataclass
class PageType:
    """Page type classification."""
    type: Literal[
        "ecommerce_product",
        "ecommerce_collection",
        "ecommerce_checkout",
        "saas_home",
        "saas_pricing",
        "saas_signup",
        "marketplace",
        "local_service",
        "leadgen_landing",
        "course_or_education",
        "content_blog",
        "app_download",
        "enterprise_b2b",
        "personal_brand_consultant",
        "b2b_corporate_service",
        "unknown"
    ]
    confidence: float
    signals: Dict[str, Any]


def detect_page_type(
    url: str,
    page_text: str,
    page_map: Optional[Dict[str, Any]],
    intent: Any,  # PageIntent from brand_context
    brand_ctx: Any  # BrandContext from brand_context
) -> PageType:
    """
    Detect page type using heuristics.
    
    Args:
        url: Page URL
        page_text: Page text content
        page_map: Page map with headlines, CTAs, etc.
        intent: Detected page intent (PageIntent)
        brand_ctx: Brand context (BrandContext)
        
    Returns:
        PageType with detected type and confidence
    """
    url_lower = url.lower()
    page_text_lower = (page_text or "").lower()
    
    signals = {}
    type_scores = {
        "ecommerce_product": 0.0,
        "ecommerce_collection": 0.0,
        "ecommerce_checkout": 0.0,
        "saas_home": 0.0,
        "saas_pricing": 0.0,
        "saas_signup": 0.0,
        "marketplace": 0.0,
        "local_service": 0.0,
        "leadgen_landing": 0.0,
        "course_or_education": 0.0,
        "content_blog": 0.0,
        "app_download": 0.0,
        "enterprise_b2b": 0.0,
        "personal_brand_consultant": 0.0,
        "b2b_corporate_service": 0.0,
    }
    
    # Ecommerce Product
    ecommerce_keywords = ["add to cart", "buy now", "shipping", "returns", "sku", "size", "color", "quantity", "in stock", "out of stock"]
    ecommerce_matches = sum(1 for kw in ecommerce_keywords if kw in page_text_lower)
    if "/product" in url_lower or "/products/" in url_lower:
        type_scores["ecommerce_product"] += 3.0
        signals["ecommerce_product_url"] = True
    if ecommerce_matches > 0:
        type_scores["ecommerce_product"] += min(ecommerce_matches * 0.4, 2.5)
        signals["ecommerce_keywords"] = ecommerce_matches
    
    # Ecommerce Collection
    if "/collection" in url_lower or "/collections/" in url_lower or "/category" in url_lower:
        type_scores["ecommerce_collection"] += 3.0
        signals["collection_url"] = True
    if "browse" in page_text_lower and "products" in page_text_lower:
        type_scores["ecommerce_collection"] += 1.0
    
    # Ecommerce Checkout
    checkout_keywords = ["checkout", "payment", "delivery address", "order summary", "billing", "shipping address"]
    checkout_matches = sum(1 for kw in checkout_keywords if kw in page_text_lower)
    if "/cart" in url_lower or "/checkout" in url_lower:
        type_scores["ecommerce_checkout"] += 4.0
        signals["checkout_url"] = True
    if checkout_matches > 0:
        type_scores["ecommerce_checkout"] += min(checkout_matches * 0.5, 2.0)
        signals["checkout_keywords"] = checkout_matches
    
    # SaaS Home
    saas_keywords = ["platform", "dashboard", "integrations", "api", "start free trial", "sign up", "features"]
    saas_matches = sum(1 for kw in saas_keywords if kw in page_text_lower)
    if saas_matches >= 3 and "/pricing" not in url_lower and "/signup" not in url_lower:
        type_scores["saas_home"] += min(saas_matches * 0.4, 2.5)
        signals["saas_keywords"] = saas_matches
    
    # SaaS Pricing
    if intent and intent.intent == "pricing":
        type_scores["saas_pricing"] += 3.0
        signals["pricing_intent"] = True
    if "/pricing" in url_lower and saas_matches > 0:
        type_scores["saas_pricing"] += 2.0
        signals["saas_pricing_url"] = True
    
    # SaaS Signup
    if "/signup" in url_lower or "/sign-up" in url_lower or "/register" in url_lower:
        type_scores["saas_signup"] += 3.0
        signals["signup_url"] = True
    if "create account" in page_text_lower or "sign up" in page_text_lower:
        type_scores["saas_signup"] += 1.5
    
    # Marketplace
    marketplace_keywords = ["listings", "sellers", "buyers", "categories", "compare offers", "multiple sellers"]
    marketplace_matches = sum(1 for kw in marketplace_keywords if kw in page_text_lower)
    if marketplace_matches >= 2:
        type_scores["marketplace"] += min(marketplace_matches * 0.5, 2.5)
        signals["marketplace_keywords"] = marketplace_matches
    
    # Local Service
    local_keywords = ["book appointment", "call now", "location", "hours", "clinic", "directions", "whatsapp", "visit us", "our location"]
    local_matches = sum(1 for kw in local_keywords if kw in page_text_lower)
    if local_matches >= 2:
        type_scores["local_service"] += min(local_matches * 0.5, 2.5)
        signals["local_keywords"] = local_matches
    
    # Leadgen Landing
    leadgen_keywords = ["book a call", "get a quote", "free consultation", "request audit", "contact form", "schedule"]
    leadgen_matches = sum(1 for kw in leadgen_keywords if kw in page_text_lower)
    calendly_hints = "calendly" in page_text_lower or "schedule" in page_text_lower
    if leadgen_matches >= 2 or (leadgen_matches > 0 and calendly_hints):
        type_scores["leadgen_landing"] += min(leadgen_matches * 0.5, 2.5)
        signals["leadgen_keywords"] = leadgen_matches
        if calendly_hints:
            signals["calendly_hint"] = True
    
    # Course/Education
    course_keywords = ["curriculum", "lessons", "syllabus", "enroll", "certificate", "instructor", "course", "module"]
    course_matches = sum(1 for kw in course_keywords if kw in page_text_lower)
    if course_matches >= 3:
        type_scores["course_or_education"] += min(course_matches * 0.4, 2.5)
        signals["course_keywords"] = course_matches
    
    # Content Blog
    if intent and intent.intent == "blog":
        type_scores["content_blog"] += 3.0
        signals["blog_intent"] = True
    if "/blog" in url_lower and "subscribe" in page_text_lower:
        type_scores["content_blog"] += 2.0
        signals["blog_subscribe"] = True
    
    # App Download
    app_keywords = ["app store", "google play", "download the app", "get the app", "mobile app"]
    app_matches = sum(1 for kw in app_keywords if kw in page_text_lower)
    if app_matches >= 2:
        type_scores["app_download"] += min(app_matches * 0.6, 2.5)
        signals["app_keywords"] = app_matches
    
    # Personal Brand / Consultant
    personal_keywords = ["work with me", "consultant", "strategist", "advisor", "coach", "expert"]
    personal_matches = sum(1 for kw in personal_keywords if kw in page_text_lower)
    personal_ctas = ["work with me", "book a call", "contact", "let's talk"]
    personal_cta_matches = sum(1 for cta in personal_ctas if cta in page_text_lower)
    
    # Check if person name is prominent (in H1 or title)
    person_name_prominent = False
    if page_map:
        headlines = page_map.get("headlines", [])
        title = page_map.get("title", "")
        # Extract potential person name from domain
        domain = urlparse(url).netloc.lower().replace("www.", "").split(".")[0]
        
        # Check if person name appears in H1 or title
        for h in headlines:
            if isinstance(h, dict) and h.get("tag") == "h1":
                h1_text = h.get("text", "").lower()
                if domain in h1_text or any(word in h1_text for word in domain.split("-")):
                    person_name_prominent = True
                    break
        if domain in title.lower():
            person_name_prominent = True
    
    # No ecommerce signals (no cart, no pricing grid)
    has_ecommerce_signals = any(kw in page_text_lower for kw in ["add to cart", "buy now", "checkout", "shopping cart"])
    
    if personal_matches >= 2 and personal_cta_matches > 0 and not has_ecommerce_signals:
        type_scores["personal_brand_consultant"] += min(personal_matches * 0.6, 3.0)
        signals["personal_keywords"] = personal_matches
        signals["personal_ctas"] = personal_cta_matches
        if person_name_prominent:
            type_scores["personal_brand_consultant"] += 2.0
            signals["person_name_prominent"] = True
    
    # B2B Corporate Service
    b2b_keywords = ["solutions", "projects", "clients", "industries", "services", "team", "portfolio"]
    b2b_matches = sum(1 for kw in b2b_keywords if kw in page_text_lower)
    b2b_nav_keywords = ["projects", "services", "contact", "about", "case studies"]
    b2b_nav_matches = 0
    
    if page_map:
        nav_text = " ".join([
            str(page_map.get("headlines", [])),
            str(page_map.get("ctas", []))
        ]).lower()
        b2b_nav_matches = sum(1 for kw in b2b_nav_keywords if kw in nav_text)
    
    # No instant purchase flow
    has_instant_purchase = any(kw in page_text_lower for kw in ["add to cart", "buy now", "purchase", "checkout"])
    
    if b2b_matches >= 3 and b2b_nav_matches >= 2 and not has_instant_purchase:
        type_scores["b2b_corporate_service"] += min(b2b_matches * 0.5, 3.0)
        signals["b2b_keywords"] = b2b_matches
        signals["b2b_nav"] = b2b_nav_matches
    
    # Enterprise B2B (keep existing logic, but check after personal/b2b)
    if brand_ctx and brand_ctx.brand_maturity == "enterprise":
        enterprise_keywords = ["compliance", "security", "soc 2", "contact sales", "rfp", "enterprise"]
        enterprise_matches = sum(1 for kw in enterprise_keywords if kw in page_text_lower)
        if enterprise_matches >= 2:
            type_scores["enterprise_b2b"] += min(enterprise_matches * 0.5, 2.5)
            signals["enterprise_keywords"] = enterprise_matches
        
        # Check nav items
        if page_map:
            nav_keywords = ["security", "enterprise", "partners", "developers"]
            nav_text = " ".join([
                str(page_map.get("headlines", [])),
                str(page_map.get("ctas", []))
            ]).lower()
            nav_matches = sum(1 for kw in nav_keywords if kw in nav_text)
            if nav_matches >= 2:
                type_scores["enterprise_b2b"] += 1.5
                signals["enterprise_nav"] = nav_matches
    
    # Find max type
    max_type = max(type_scores.items(), key=lambda x: x[1])
    page_type_name = max_type[0] if max_type[1] > 0.5 else "unknown"
    
    # Calculate confidence
    total_score = sum(type_scores.values())
    epsilon = 0.1
    confidence = max_type[1] / (total_score + epsilon) if total_score > 0 else 0.0
    confidence = min(max(confidence, 0.0), 1.0)
    
    signals["type_scores"] = type_scores
    
    return PageType(
        type=page_type_name,
        confidence=confidence,
        signals=signals
    )

