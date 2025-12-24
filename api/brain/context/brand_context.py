"""
Brand Context and Page Intent Detection

Detects brand maturity (startup/growth/enterprise) and page intent
to enable context-aware analysis that avoids naive verdicts for mature brands.
"""
from dataclasses import dataclass
from typing import Literal, Dict, Any, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

# Known enterprise domains
KNOWN_ENTERPRISE_DOMAINS = {
    "stripe.com",
    "notion.so",
    "apple.com",
    "google.com",
    "microsoft.com",
    "shopify.com",
    "adobe.com",
    "salesforce.com",
    "hubspot.com",
    "meta.com",
    "aws.amazon.com",
    "amazon.com",
    "github.com",
    "atlassian.com",
    "slack.com",
    "zoom.us",
    "dropbox.com",
    "oracle.com",
    "ibm.com",
}

# Known large ecommerce domains (treated as enterprise/growth-large)
KNOWN_LARGE_ECOMMERCE_DOMAINS = {
    "digikala.com",
    "amazon.com",
    "alibaba.com",
    "ebay.com",
    "walmart.com",
    "temu.com",
    "shein.com",
    "shopify.com",  # Already in enterprise, but also ecommerce
}

# Combined set for brand maturity detection
ALL_KNOWN_LARGE_DOMAINS = KNOWN_ENTERPRISE_DOMAINS | KNOWN_LARGE_ECOMMERCE_DOMAINS


@dataclass
class PageIntent:
    """Page intent classification."""
    intent: Literal["lead_generation", "pricing", "docs", "blog", "enterprise_sales", "product", "unknown"]
    confidence: float
    signals: Dict[str, Any]


@dataclass
class BrandContext:
    """Brand maturity and context classification."""
    brand_maturity: Literal["startup", "growth", "enterprise"]
    confidence: float
    signals: Dict[str, Any]
    analysis_mode: Literal["standard", "enterprise_context_aware"]


def normalize_domain(url: str) -> str:
    """
    Normalize domain from URL.
    
    Args:
        url: URL string or domain string
        
    Returns:
        Normalized domain (lowercase, no www)
    """
    try:
        # If it doesn't start with http/https, treat as domain
        if not url.startswith(("http://", "https://")):
            domain = url.lower()
        else:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
        
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        
        # Remove path if present (for domain-only strings)
        if "/" in domain:
            domain = domain.split("/")[0]
        
        return domain
    except Exception as e:
        logger.warning(f"Failed to parse domain from URL {url}: {e}")
        return url.lower()


def detect_page_intent(page_text: str, page_map: Optional[Dict[str, Any]], url: str) -> PageIntent:
    """
    Detect page intent using heuristics.
    
    Args:
        page_text: Page text content
        page_map: Page map with headlines, CTAs, etc.
        url: Page URL
        
    Returns:
        PageIntent with detected intent and confidence
    """
    page_text_lower = (page_text or "").lower()
    url_lower = url.lower()
    
    signals = {}
    intent_scores = {
        "pricing": 0.0,
        "docs": 0.0,
        "blog": 0.0,
        "enterprise_sales": 0.0,
        "lead_generation": 0.0,
        "product": 0.0,
    }
    
    # Pricing detection
    pricing_keywords = ["pricing", "plan", "plans", "per month", "per user", "starter", "enterprise", "tier", "subscription"]
    pricing_matches = sum(1 for kw in pricing_keywords if kw in page_text_lower)
    if "/pricing" in url_lower or "pricing" in url_lower:
        intent_scores["pricing"] += 3.0
        signals["pricing_url"] = True
    if pricing_matches > 0:
        intent_scores["pricing"] += min(pricing_matches * 0.5, 2.0)
        signals["pricing_keywords"] = pricing_matches
    
    # Docs detection
    docs_keywords = ["docs", "documentation", "api reference", "developers", "developer", "api docs"]
    docs_matches = sum(1 for kw in docs_keywords if kw in page_text_lower)
    if "/docs" in url_lower or "/developers" in url_lower or "/developer" in url_lower:
        intent_scores["docs"] += 3.0
        signals["docs_url"] = True
    if docs_matches > 0:
        intent_scores["docs"] += min(docs_matches * 0.4, 2.0)
        signals["docs_keywords"] = docs_matches
    
    # Blog detection
    if "/blog" in url_lower:
        intent_scores["blog"] += 3.0
        signals["blog_url"] = True
    if "subscribe" in page_text_lower and "blog" in page_text_lower:
        intent_scores["blog"] += 2.0
        signals["blog_subscribe"] = True
    
    # Enterprise sales detection
    enterprise_keywords = ["contact sales", "talk to sales", "request a demo", "enterprise", "sales team"]
    enterprise_matches = sum(1 for kw in enterprise_keywords if kw in page_text_lower)
    if enterprise_matches > 0:
        intent_scores["enterprise_sales"] += min(enterprise_matches * 0.6, 2.5)
        signals["enterprise_keywords"] = enterprise_matches
    
    # Check for sales CTAs in page_map
    if page_map:
        ctas = page_map.get("ctas", [])
        sales_cta_count = sum(1 for cta in ctas if isinstance(cta, dict) and "sales" in str(cta.get("label", "")).lower())
        if sales_cta_count > 0:
            intent_scores["enterprise_sales"] += sales_cta_count * 0.5
            signals["sales_ctas"] = sales_cta_count
    
    # Lead generation detection
    lead_keywords = ["book a call", "get a quote", "free consultation", "request audit", "contact us", "schedule a call"]
    lead_matches = sum(1 for kw in lead_keywords if kw in page_text_lower)
    if lead_matches > 0:
        intent_scores["lead_generation"] += min(lead_matches * 0.5, 2.0)
        signals["lead_keywords"] = lead_matches
    
    # Check for forms (heuristic: presence of form-related keywords)
    form_keywords = ["form", "submit", "email", "phone", "name"]
    form_matches = sum(1 for kw in form_keywords if kw in page_text_lower)
    if form_matches >= 3 and lead_matches > 0:
        intent_scores["lead_generation"] += 1.0
        signals["form_indicators"] = form_matches
    
    # Product page (default if no strong signal)
    if max(intent_scores.values()) < 1.0:
        intent_scores["product"] = 1.0
        signals["default_product"] = True
    
    # Find max intent
    max_intent = max(intent_scores.items(), key=lambda x: x[1])
    intent_name = max_intent[0] if max_intent[1] > 0.5 else "unknown"
    
    # Calculate confidence
    total_score = sum(intent_scores.values())
    confidence = max_intent[1] / (total_score + 0.1) if total_score > 0 else 0.0
    confidence = min(confidence, 1.0)
    
    signals["intent_scores"] = intent_scores
    
    return PageIntent(
        intent=intent_name,
        confidence=confidence,
        signals=signals
    )


def detect_brand_context(
    url: str,
    page_text: str,
    page_map: Optional[Dict[str, Any]],
    intent: PageIntent
) -> BrandContext:
    """
    Detect brand maturity context.
    
    Args:
        url: Page URL
        page_text: Page text content
        page_map: Page map with headlines, CTAs, etc.
        intent: Detected page intent
        
    Returns:
        BrandContext with maturity classification
    """
    domain = normalize_domain(url)
    page_text_lower = (page_text or "").lower()
    
    signals = {}
    enterprise_score = 0.0
    growth_score = 0.0
    startup_score = 0.0
    
    # Enterprise signals (check both enterprise and large ecommerce)
    if domain in ALL_KNOWN_LARGE_DOMAINS:
        enterprise_score += 5.0
        signals["known_enterprise_domain"] = domain
        if domain in KNOWN_LARGE_ECOMMERCE_DOMAINS:
            signals["known_large_ecommerce"] = True
    
    enterprise_keywords = ["enterprise", "compliance", "security", "soc 2", "gdpr", "iso", "developers", "api"]
    enterprise_keyword_matches = sum(1 for kw in enterprise_keywords if kw in page_text_lower)
    if enterprise_keyword_matches > 0:
        enterprise_score += min(enterprise_keyword_matches * 0.5, 2.0)
        signals["enterprise_keywords"] = enterprise_keyword_matches
    
    # Check nav items (heuristic: common enterprise nav terms)
    nav_keywords = ["developers", "docs", "security", "partners", "pricing", "enterprise", "api"]
    nav_matches = sum(1 for kw in nav_keywords if kw in page_text_lower)
    if nav_matches >= 3:
        enterprise_score += 1.5
        signals["enterprise_nav_indicators"] = nav_matches
    
    # Brand density (brand name in title/H1)
    if page_map:
        headlines = page_map.get("headlines", [])
        title = page_map.get("title", "")
        
        # Extract brand name from domain
        brand_name = domain.split(".")[0] if "." in domain else domain
        
        # Check if brand appears in title/H1
        title_lower = title.lower() if title else ""
        h1_texts = [h.get("text", "").lower() if isinstance(h, dict) else str(h).lower() for h in headlines if isinstance(h, dict) and h.get("tag") == "h1"]
        
        if brand_name in title_lower or any(brand_name in h1 for h1 in h1_texts):
            enterprise_score += 1.0
            signals["high_brand_density"] = True
    
    # Growth signals
    growth_keywords = ["pricing", "tier", "plan", "case studies", "customers", "testimonials", "comparison"]
    growth_matches = sum(1 for kw in growth_keywords if kw in page_text_lower)
    if growth_matches >= 3:
        growth_score += min(growth_matches * 0.3, 2.0)
        signals["growth_indicators"] = growth_matches
    
    # Startup signals
    startup_keywords = ["work with me", "personal brand", "freelance", "consultant"]
    startup_matches = sum(1 for kw in startup_keywords if kw in page_text_lower)
    if startup_matches > 0:
        startup_score += startup_matches * 0.5
        signals["startup_indicators"] = startup_matches
    
    # Check for limited nav (heuristic: fewer nav items suggests startup)
    if page_map:
        ctas = page_map.get("ctas", [])
        if len(ctas) <= 2:
            startup_score += 0.5
            signals["limited_ctas"] = len(ctas)
    
    # Determine brand maturity
    scores = {
        "enterprise": enterprise_score,
        "growth": growth_score,
        "startup": startup_score
    }
    max_maturity = max(scores.items(), key=lambda x: x[1])
    brand_maturity = max_maturity[0] if max_maturity[1] > 0.5 else "growth"  # Default to growth
    
    # Calculate confidence
    total_score = sum(scores.values())
    epsilon = 0.1
    confidence = max_maturity[1] / (total_score + epsilon) if total_score > 0 else 0.5
    confidence = min(max(confidence, 0.0), 1.0)
    
    signals["maturity_scores"] = scores
    
    # Determine analysis mode
    if brand_maturity == "enterprise" and intent.intent in ["pricing", "docs", "product", "enterprise_sales"]:
        analysis_mode = "enterprise_context_aware"
    else:
        analysis_mode = "standard"
    
    return BrandContext(
        brand_maturity=brand_maturity,
        confidence=confidence,
        signals=signals,
        analysis_mode=analysis_mode
    )


def build_context(url: str, page_text: str, page_map: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build complete context (intent + brand + page_type).
    
    Args:
        url: Page URL
        page_text: Page text content
        page_map: Page map with headlines, CTAs, etc.
        
    Returns:
        Dictionary with brand_context, page_intent, and page_type
    """
    intent = detect_page_intent(page_text, page_map, url)
    brand_ctx = detect_brand_context(url, page_text, page_map, intent)
    
    # Detect page type
    from api.brain.context.page_type import detect_page_type
    page_type = detect_page_type(url, page_text, page_map, intent, brand_ctx)
    
    # Check if debug signals should be included
    import os
    context_signals_debug = os.getenv("CONTEXT_SIGNALS_DEBUG", "true").lower() == "true"
    
    return {
        "brand_context": {
            "brand_maturity": brand_ctx.brand_maturity,
            "confidence": brand_ctx.confidence,
            "analysis_mode": brand_ctx.analysis_mode,
            **({"signals": brand_ctx.signals} if context_signals_debug else {})
        },
        "page_intent": {
            "intent": intent.intent,
            "confidence": intent.confidence,
            **({"signals": intent.signals} if context_signals_debug else {})
        },
        "page_type": {
            "type": page_type.type,
            "confidence": page_type.confidence,
            **({"signals": page_type.signals} if context_signals_debug else {})
        }
    }

