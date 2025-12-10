"""
Decision Snapshot Extractor

Extracts ONLY decision-critical elements from a landing page:
- Hero headline
- Hero subheadline
- Primary CTA text
- Visible price
- Guarantee / return / risk text

DO NOT extract full page content.
"""

import re
import logging
from typing import Optional, Dict
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Import Playwright-based URL renderer (ASYNC ONLY)
try:
    from api.utils.url_renderer_async import render_url_with_js
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    # Fallback to requests if Playwright is not available
    import requests

logger = logging.getLogger("decision_snapshot")


def is_valid_url(url: str) -> bool:
    """Check if input is a valid URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def detect_channel(url: str) -> str:
    """
    Detect channel type based on URL domain.
    
    Args:
        url: URL to analyze
        
    Returns:
        "marketplace_product" for marketplace domains, "generic_saas" otherwise
    """
    try:
        parsed = urlparse(url.lower())
        domain = parsed.netloc.lower()
        # Remove www. prefix if present
        domain = domain.replace("www.", "")
        
        # Marketplace domains
        marketplace_domains = ["amazon", "trendyol", "ebay", "zalando", "booking", "airbnb"]
        
        for marketplace in marketplace_domains:
            if marketplace in domain:
                return "marketplace_product"
        
        # Default to generic_saas
        return "generic_saas"
    except Exception:
        # If URL parsing fails, default to generic_saas
        return "generic_saas"


async def extract_decision_snapshot(url: str) -> Dict[str, any]:
    """
    Extract decision-critical elements from a URL.
    
    Args:
        url: URL to extract from
        
    Returns:
        Dict with keys:
        - hero_headline, hero_subheadline, cta, price, guarantee_risk
        - has_free_returns, has_delivery_date, has_ratings, has_trust_badges
        
    Raises:
        ValueError: If URL is invalid or page cannot be fetched
        ValueError: If insufficient decision-critical elements are found
    """
    if not is_valid_url(url):
        raise ValueError(f"Invalid URL: {url}")
    
    # Ensure URL has scheme
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        # Use Playwright to render JavaScript-heavy pages (ASYNC)
        if PLAYWRIGHT_AVAILABLE:
            logger.info(f"[Decision Snapshot] Using Playwright Async to render URL: {url}")
            html = await render_url_with_js(url, timeout=60000, wait_until="networkidle")  # 60 seconds timeout
        else:
            # Fallback to requests if Playwright is not available
            logger.warning("[Decision Snapshot] Playwright not available, falling back to requests")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
            }
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=30, allow_redirects=True)
            
            # Handle 403 Forbidden specifically
            if response.status_code == 403:
                raise ValueError(
                    "This website blocks automated access (403 Forbidden). "
                    "Many e-commerce sites like Trendyol, Amazon, etc. use anti-bot protection. "
                    "\n\nSOLUTION: Please manually copy and paste the following from the page:\n"
                    "- Hero headline\n"
                    "- CTA button text\n"
                    "- Price (if visible)\n"
                    "- Guarantee/refund information (if present)\n\n"
                    "Then paste this content directly in the input field (not the URL)."
                )
            
            response.raise_for_status()
            html = response.text
        
    except ValueError as ve:
        # Re-raise ValueError (from Playwright or our custom errors) as-is
        raise ve
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Decision Snapshot] Error fetching URL {url}: {error_msg}")
        
        # Check for common error patterns
        if "403" in error_msg or "forbidden" in error_msg.lower():
            raise ValueError(
                "This website blocks automated access (403 Forbidden). "
                "Many e-commerce sites like Trendyol, Amazon, etc. use anti-bot protection. "
                "\n\nSOLUTION: Please manually copy and paste the following from the page:\n"
                "- Hero headline\n"
                "- CTA button text\n"
                "- Price (if visible)\n"
                "- Guarantee/refund information (if present)\n\n"
                "Then paste this content directly in the input field (not the URL)."
            )
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            raise ValueError(
                "The request timed out. Please manually copy and paste the page content "
                "(headline, CTA, price, guarantee info) instead of using the URL."
            )
        raise ValueError(f"Failed to fetch URL: {e}")
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        raise ValueError(f"Failed to parse HTML: {e}")
    
    # Extract elements
    snapshot = {
        'hero_headline': None,
        'hero_subheadline': None,
        'cta': None,
        'price': None,
        'guarantee_risk': None
    }
    
    # Hero headline - look for h1 in hero section or first prominent h1
    hero_headline = None
    # Try common hero selectors
    hero_selectors = [
        'h1.hero-title', 'h1.hero-headline', '.hero h1', 
        'header h1', '.hero-section h1', 'section.hero h1',
        'h1'  # Fallback to first h1
    ]
    for selector in hero_selectors:
        element = soup.select_one(selector)
        if element:
            hero_headline = element.get_text(strip=True)
            if hero_headline:
                break
    
    snapshot['hero_headline'] = hero_headline
    
    # Hero subheadline - look for subtitle near hero
    hero_subheadline = None
    subheadline_selectors = [
        'h2.hero-subtitle', '.hero-subtitle', '.hero h2',
        'h2.subheadline', '.subheadline', 'p.hero-description',
        '.hero p'  # Fallback
    ]
    for selector in subheadline_selectors:
        element = soup.select_one(selector)
        if element:
            hero_subheadline = element.get_text(strip=True)
            if hero_subheadline and len(hero_subheadline) < 200:  # Reasonable length
                break
    
    snapshot['hero_subheadline'] = hero_subheadline
    
    # Primary CTA - look for buttons with common CTA text
    cta = None
    cta_keywords = ['buy', 'purchase', 'order', 'book', 'sign up', 'get started', 
                    'add to cart', 'checkout', 'subscribe', 'join', 'try', 'start']
    
    # Look for buttons/links with CTA keywords
    buttons = soup.find_all(['button', 'a'], class_=re.compile(r'btn|cta|button|primary', re.I))
    for btn in buttons:
        text = btn.get_text(strip=True).lower()
        if any(keyword in text for keyword in cta_keywords):
            cta = btn.get_text(strip=True)
            break
    
    # Fallback: look for any button with "primary" class
    if not cta:
        primary_btn = soup.find(['button', 'a'], class_=re.compile(r'primary', re.I))
        if primary_btn:
            cta = primary_btn.get_text(strip=True)
    
    snapshot['cta'] = cta
    
    # Price - look for price patterns
    price = None
    price_patterns = [
        r'\$\d+[\d,.]*',  # $99.99
        r'\d+[\d,.]*\s*(?:TL|TRY|USD|EUR|£)',  # 99.99 TL
        r'(?:price|cost|fee)[:\s]*\$?\d+',  # Price: $99
    ]
    
    # Look in common price locations
    price_selectors = ['.price', '.pricing', '[class*="price"]', '[id*="price"]']
    for selector in price_selectors:
        elements = soup.select(selector)
        for elem in elements:
            text = elem.get_text()
            for pattern in price_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    price = match.group(0)
                    break
            if price:
                break
        if price:
            break
    
    snapshot['price'] = price
    
    # Guarantee / Risk text - look for guarantee/refund/cancellation mentions
    guarantee_risk = None
    guarantee_keywords = ['guarantee', 'refund', 'money back', 'cancel', 
                         'return', 'risk-free', 'satisfaction', 'warranty']
    
    # Look for guarantee text in common locations
    guarantee_selectors = [
        '[class*="guarantee"]', '[class*="refund"]', '[class*="risk"]',
        '.guarantee', '.refund-policy', '.cancellation'
    ]
    
    for selector in guarantee_selectors:
        elements = soup.select(selector)
        for elem in elements:
            text = elem.get_text(strip=True)
            if any(keyword in text.lower() for keyword in guarantee_keywords):
                # Take first reasonable length snippet
                if len(text) < 200:
                    guarantee_risk = text
                else:
                    # Extract relevant sentence
                    sentences = re.split(r'[.!?]', text)
                    for sentence in sentences:
                        if any(keyword in sentence.lower() for keyword in guarantee_keywords):
                            guarantee_risk = sentence.strip()
                            break
                if guarantee_risk:
                    break
        if guarantee_risk:
            break
    
    # Fallback: search entire page for guarantee keywords
    if not guarantee_risk:
        all_text = soup.get_text()
        for keyword in guarantee_keywords:
            pattern = rf'.{{0,100}}{re.escape(keyword)}.{{0,100}}'
            match = re.search(pattern, all_text, re.I)
            if match:
                guarantee_risk = match.group(0).strip()
                break
    
    snapshot['guarantee_risk'] = guarantee_risk
    
    # Detect trust signals
    has_free_returns = False
    has_delivery_date = False
    has_ratings = False
    has_trust_badges = False
    
    # Check for free returns
    free_return_keywords = ['free return', 'free returns', 'free shipping and return', 
                           'free returns & exchanges', 'hassle-free return']
    page_text_lower = soup.get_text().lower()
    if any(keyword in page_text_lower for keyword in free_return_keywords):
        has_free_returns = True
    
    # Check for delivery date information
    delivery_keywords = ['delivery', 'arrives', 'estimated delivery', 'ships', 
                        'delivery by', 'get it by', 'ships from', 'dispatch']
    delivery_selectors = ['[class*="delivery"]', '[class*="shipping"]', '[id*="delivery"]']
    for selector in delivery_selectors:
        if soup.select_one(selector):
            has_delivery_date = True
            break
    if not has_delivery_date and any(keyword in page_text_lower for keyword in delivery_keywords):
        has_delivery_date = True
    
    # Check for ratings/reviews
    rating_selectors = [
        '[class*="rating"]', '[class*="review"]', '[class*="star"]',
        '[data-rating]', '.rating', '.reviews', '[aria-label*="star"]'
    ]
    for selector in rating_selectors:
        if soup.select_one(selector):
            has_ratings = True
            break
    if not has_ratings:
        # Check for rating text patterns
        rating_patterns = [r'\d+\.?\d*\s*stars?', r'\d+\/\d+\s*stars?', 
                          r'\d+\s*reviews?', r'rating:\s*\d+']
        for pattern in rating_patterns:
            if re.search(pattern, page_text_lower):
                has_ratings = True
                break
    
    # Check for trust badges (Amazon Prime, Verified Purchase, Best Seller, etc.)
    trust_badge_keywords = ['prime', 'verified', 'best seller', 'amazon\'s choice',
                           'top rated', 'customer favorite', 'popular', 'trusted seller']
    trust_badge_selectors = [
        '[class*="badge"]', '[class*="trust"]', '[class*="verified"]',
        '[class*="prime"]', '[aria-label*="badge"]', '[data-badge]'
    ]
    for selector in trust_badge_selectors:
        if soup.select_one(selector):
            has_trust_badges = True
            break
    if not has_trust_badges:
        for keyword in trust_badge_keywords:
            if keyword in page_text_lower:
                has_trust_badges = True
                break
    
    # Add trust signals to snapshot
    snapshot['has_free_returns'] = has_free_returns
    snapshot['has_delivery_date'] = has_delivery_date
    snapshot['has_ratings'] = has_ratings
    snapshot['has_trust_badges'] = has_trust_badges
    
    # Detect channel type
    snapshot['channel'] = detect_channel(url)
    
    # Validate we have at least one critical element
    critical_elements = [
        snapshot['hero_headline'],
        snapshot['cta'],
        snapshot['price'] or snapshot['guarantee_risk']
    ]
    
    if not any(critical_elements):
        raise ValueError(
            "This page does not expose enough decision-critical elements. "
            "Could not find hero headline, CTA, or price/guarantee information."
        )
    
    return snapshot


def format_snapshot_text(snapshot: Dict[str, Optional[str]]) -> str:
    """
    Format snapshot into normalized text format.
    
    Args:
        snapshot: Dict from extract_decision_snapshot
        
    Returns:
        Formatted text string
    """
    parts = []
    
    parts.append(f"HERO HEADLINE: {snapshot['hero_headline'] or '[Not visible]'}")
    parts.append(f"HERO SUBHEADLINE: {snapshot['hero_subheadline'] or '[Not visible]'}")
    parts.append(f"CTA: {snapshot['cta'] or '[Not visible]'}")
    parts.append(f"PRICE: {snapshot['price'] or '[Not visible]'}")
    parts.append(f"GUARANTEE / RISK: {snapshot['guarantee_risk'] or '[Not visible]'}")
    
    return "\n".join(parts)

