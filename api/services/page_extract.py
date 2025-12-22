"""
Extract structured data from page DOM:
- Headlines (H1/H2)
- CTAs (buttons, links, form inputs)
- Trust signals (keywords-based)
"""
from typing import Dict, Any, List
from bs4 import BeautifulSoup


def _text(el):
    """Extract clean text from an element."""
    if not el:
        return ""
    return " ".join(el.get_text(" ", strip=True).split())


def extract_page_map(capture: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract page structure from captured HTML:
    - Headlines (H1, H2)
    - CTAs (links, buttons, submit inputs)
    - Trust signals (keyword-based detection)
    
    Args:
        capture: Dictionary from capture_page_artifacts()
        
    Returns:
        Dictionary with headlines, ctas, trust_signals, etc.
    """
    # Ensure capture is a dict
    if not isinstance(capture, dict):
        capture = {}
    
    # Safely get HTML
    dom = capture.get("dom", {}) if isinstance(capture, dict) else {}
    html = dom.get("html_excerpt", "") if isinstance(dom, dict) else ""
    soup = BeautifulSoup(html, "lxml")
    
    # Extract headlines
    headlines: List[Dict[str, Any]] = []
    for tag in ["h1", "h2"]:
        for el in soup.find_all(tag)[:10]:
            txt = _text(el)
            if txt:
                headlines.append({
                    "tag": tag,
                    "text": txt,
                    "where": {
                        "section": "unknown",
                        "selector": f"{tag}",
                        "bbox": [0, 0, 0, 0]
                    }
                })
    
    # Extract CTAs
    ctas: List[Dict[str, Any]] = []
    # a/button/input submit as basic CTA candidates
    for el in soup.select("a,button,input[type='submit'],input[type='button']")[:30]:
        label = _text(el) or (el.get("value") or "")
        href = el.get("href") or ""
        
        if not label and not href:
            continue
        
        ctas.append({
            "label": label[:80],
            "type": "primary" if len(ctas) == 0 else "secondary",
            "href": href,
            "where": {
                "section": "unknown",
                "selector": el.name,
                "bbox": [0, 0, 0, 0]
            },
            "notes": ""
        })
    
    # Very light trust signal extraction (keywords)
    trust_signals: List[Dict[str, Any]] = []
    dom = capture.get("dom", {}) if isinstance(capture, dict) else {}
    text = (dom.get("readable_text_excerpt", "") if isinstance(dom, dict) else "" or "").lower()
    
    trust_keywords = [
        "testimonial", "review", "rating", "clients", "trusted",
        "guarantee", "policy", "privacy", "terms"
    ]
    
    for kw in trust_keywords:
        if kw in text:
            trust_signals.append({
                "type": "policy" if kw in ["privacy", "terms", "policy"] else "testimonial",
                "text_or_label": kw,
                "where": {
                    "section": "unknown",
                    "selector": "body",
                    "bbox": [0, 0, 0, 0]
                }
            })
    
    return {
        "headlines": headlines,
        "ctas": ctas,
        "trust_signals": trust_signals,
        "offer_elements": [],
        "forms": [],
        "navigation": {
            "items": [],
            "language_switch": False
        }
    }

