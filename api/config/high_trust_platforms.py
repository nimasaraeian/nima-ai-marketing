"""
High-Trust Platform Configuration

Platforms where users have high baseline trust,
so "Risk Not Addressed" blocker should be suppressed
when trust signals are present.
"""

HIGH_TRUST_PLATFORMS = [
    "amazon",
    "booking",
    "airbnb",
    "zalando",
    "trendyol",
    "ebay",
]


def is_high_trust_platform(url: str) -> bool:
    """
    Check if URL belongs to a high-trust platform.
    
    Args:
        url: URL to check
        
    Returns:
        True if platform is in high-trust list
    """
    from urllib.parse import urlparse
    
    try:
        parsed = urlparse(url.lower())
        domain = parsed.netloc.lower()
        # Remove www. prefix if present
        domain = domain.replace("www.", "")
        # Get base domain (e.g., "amazon.com" from "www.amazon.com.tr")
        domain_parts = domain.split(".")
        if len(domain_parts) >= 2:
            base_domain = domain_parts[-2]  # e.g., "amazon" from "amazon.com.tr"
            return base_domain in HIGH_TRUST_PLATFORMS
        return False
    except Exception:
        return False









