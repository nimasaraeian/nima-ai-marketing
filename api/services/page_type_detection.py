"""
Page type detection for context-aware decision analysis.

Detects page type before applying decision rules to prevent invalid recommendations
(e.g., consultation CTA suggestions for marketplaces like Digikala).
"""
from typing import Dict, Any, Literal, Optional
import re

PageType = Literal[
    "service_landing",
    "saas_landing", 
    "ecommerce_marketplace",
    "content_site",
    "brand_homepage"
]


def detect_page_type(
    url: str,
    page_map: Optional[Dict[str, Any]] = None,
    capture: Optional[Dict[str, Any]] = None
) -> PageType:
    """
    Detect page type using rule-based heuristics.
    
    Args:
        url: Page URL
        page_map: Extracted page structure (headlines, CTAs, etc.)
        capture: Page capture artifacts (optional, for future use with screenshots)
        
    Returns:
        Detected page type
    """
    if not isinstance(page_map, dict):
        page_map = {}
    if not isinstance(capture, dict):
        capture = {}
    
    # Extract text content for analysis
    headlines = page_map.get("headlines", []) if isinstance(page_map.get("headlines"), list) else []
    ctas = page_map.get("ctas", []) if isinstance(page_map.get("ctas"), list) else []
    
    # Get readable text from capture
    dom = capture.get("dom", {}) if isinstance(capture, dict) else {}
    readable_text = (dom.get("readable_text_excerpt", "") or "").lower()
    
    # Combine all text for analysis
    all_text = readable_text
    for h in headlines:
        if isinstance(h, dict):
            all_text += " " + (h.get("text", "") or "").lower()
    for cta in ctas:
        if isinstance(cta, dict):
            all_text += " " + (cta.get("label", "") or "").lower()
            all_text += " " + (cta.get("text", "") or "").lower()
    
    # URL-based detection (domain patterns)
    url_lower = url.lower()
    
    # E-commerce marketplace indicators
    marketplace_domains = [
        "digikala", "amazon", "ebay", "alibaba", "trendyol", 
        "hepsiburada", "n11", "gittigidiyor", "ciceksepeti"
    ]
    marketplace_keywords = [
        "marketplace", "shop", "store", "buy", "cart", "checkout",
        "product", "products", "catalog", "category", "categories"
    ]
    
    # Check for marketplace
    is_marketplace_domain = any(domain in url_lower for domain in marketplace_domains)
    has_product_grid_signals = (
        "product" in all_text and "price" in all_text and
        ("grid" in all_text or "catalog" in all_text or "category" in all_text)
    )
    has_search_dominance = (
        "search" in all_text and len([c for c in ctas if isinstance(c, dict) and "search" in (c.get("label", "") or "").lower()]) > 0
    )
    has_price_tags = bool(re.search(r'\$\d+|\d+\s*(tl|usd|eur|تومان|ریال)', all_text, re.IGNORECASE))
    
    if is_marketplace_domain or (has_product_grid_signals and has_price_tags) or has_search_dominance:
        return "ecommerce_marketplace"
    
    # SaaS landing indicators
    saas_keywords = [
        "software", "platform", "dashboard", "api", "integration",
        "trial", "subscription", "pricing", "features", "plans",
        "start free trial", "sign up", "login", "dashboard"
    ]
    has_saas_signals = (
        any(kw in all_text for kw in saas_keywords) and
        ("pricing" in all_text or "plan" in all_text or "trial" in all_text)
    )
    has_single_cta = len([c for c in ctas if isinstance(c, dict) and c.get("type") == "primary"]) == 1
    
    if has_saas_signals and has_single_cta:
        return "saas_landing"
    
    # Content site indicators
    content_keywords = [
        "blog", "article", "read", "news", "magazine", "post",
        "author", "published", "category", "tag", "archive"
    ]
    has_content_signals = (
        any(kw in all_text for kw in content_keywords) and
        len(headlines) > 2 and
        len([c for c in ctas if isinstance(c, dict) and "read" in (c.get("label", "") or "").lower()]) > 0
    )
    
    if has_content_signals:
        return "content_site"
    
    # Service landing indicators (default for most business pages)
    service_keywords = [
        "service", "consultation", "book", "appointment", "quote",
        "contact", "call", "request", "get started", "learn more"
    ]
    has_service_signals = (
        any(kw in all_text for kw in service_keywords) or
        len([c for c in ctas if isinstance(c, dict) and any(kw in (c.get("label", "") or "").lower() for kw in ["book", "consult", "contact", "quote"])]) > 0
    )
    has_hero_headline = (
        len(headlines) > 0 and
        isinstance(headlines[0], dict) and
        headlines[0].get("tag") == "h1"
    )
    
    if has_service_signals and has_hero_headline:
        return "service_landing"
    
    # Brand homepage (fallback for generic brand sites)
    if len(headlines) > 0 and len(ctas) == 0:
        return "brand_homepage"
    
    # Default to service_landing if uncertain
    return "service_landing"


def get_applicable_rules_for_page_type(page_type: PageType) -> Dict[str, Any]:
    """
    Get decision rules applicable to a specific page type.
    
    Returns a map of rule IDs to their applicability.
    """
    # Rules that apply to all page types
    universal_rules = {
        "clarity_weak_h1": True,
        "trust_low": True,
    }
    
    # Rules specific to page types
    page_type_rules = {
        "service_landing": {
            "clarity_weak_h1": True,
            "cta_missing": True,  # Service pages need clear CTAs
            "trust_low": True,
        },
        "saas_landing": {
            "clarity_weak_h1": True,
            "cta_missing": True,  # SaaS pages need CTAs
            "trust_low": True,
        },
        "ecommerce_marketplace": {
            "clarity_weak_h1": False,  # Marketplaces don't need H1 clarity rules
            "cta_missing": False,  # Marketplaces have product CTAs, not consultation CTAs
            "trust_low": True,  # Trust still matters
        },
        "content_site": {
            "clarity_weak_h1": True,
            "cta_missing": False,  # Content sites may not need CTAs
            "trust_low": False,  # Less critical for content
        },
        "brand_homepage": {
            "clarity_weak_h1": True,
            "cta_missing": False,  # Brand pages may not need CTAs
            "trust_low": True,
        },
    }
    
    return page_type_rules.get(page_type, universal_rules)


