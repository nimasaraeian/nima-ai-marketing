"""
Extract structured data from page DOM:
- Headlines (H1/H2)
- CTAs (buttons, links, form inputs)
- Trust signals (keywords-based)
"""
import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup


def _text(el):
    """Extract clean text from an element."""
    if not el:
        return ""
    return " ".join(el.get_text(" ", strip=True).split())


# Regex for detecting action-related CSS classes
ACTION_CLASS_RE = re.compile(r"\b(btn|button|cta|primary|secondary)\b", re.I)

# Regex for detecting action-related text content
ACTION_TEXT_RE = re.compile(
    r"\b(work with me|contact|book|request|get|start|try|schedule|call|apply|hire|download|see pricing|view pricing)\b",
    re.I
)


def _is_in_nav_or_footer(el) -> tuple[bool, bool]:
    """
    Check if element is inside nav or footer.
    Uses DOM traversal to find closest nav/footer parent.
    
    Returns:
        (in_nav, in_footer) tuple
    """
    if not el:
        return False, False
    
    # Traverse up the DOM tree
    current = el.parent
    while current:
        tag_name = current.name if hasattr(current, 'name') else None
        if tag_name:
            tag_lower = tag_name.lower()
            if tag_lower == "nav":
                return True, False
            if tag_lower == "footer":
                return False, True
        # Move to parent
        if hasattr(current, 'parent'):
            current = current.parent
        else:
            break
    
    return False, False


def bucket_for_element(
    tag_name: str,
    role: Optional[str],
    type_attr: Optional[str],
    class_name: str,
    text: str,
    in_nav: bool,
    in_footer: bool
) -> str:
    """
    Determine bucket for a CTA element based on its context and attributes.
    
    Rules:
    - If in nav → "nav"
    - If in footer → "footer"
    - If button or has button-like attributes → "action"
    - If text matches action patterns → "action"
    - Otherwise → "content"
    """
    if in_nav:
        return "nav"
    if in_footer:
        return "footer"
    
    # ACTION by element semantics
    if tag_name == "button":
        return "action"
    if role and role.lower() == "button":
        return "action"
    if type_attr and type_attr.lower() in ("submit", "button"):
        return "action"
    if class_name and ACTION_CLASS_RE.search(class_name):
        return "action"
    
    # ACTION by text (CRITICAL FIX)
    if text and ACTION_TEXT_RE.search(text):
        return "action"
    
    return "content"


def extract_hero_text(soup) -> tuple[Optional[str], Optional[str]]:
    """
    Extract hero headline and subheadline from DOM.
    
    Returns:
        (headline, subheadline) tuple
    """
    # Try main h1 first
    main = soup.select_one("main") or soup
    h1 = main.select_one("h1")
    headline = h1.get_text(" ", strip=True) if h1 else None
    
    sub = None
    if h1:
        # Try nearest paragraph in same section/container
        container = h1.parent
        p = None
        if container:
            p = container.find("p")
        if not p:
            # Fallback: first p in main
            p = main.select_one("p")
        sub = p.get_text(" ", strip=True) if p else None
    
    # Fallback: meta title if no h1
    if not headline:
        title = soup.select_one("title")
        headline = title.get_text(" ", strip=True) if title else None
    
    return headline, sub


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
    
    # Extract hero_headline and subheadline from DOM
    hero_headline, subheadline = extract_hero_text(soup)
    
    # Extract headlines (for backward compatibility)
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
    
    # Extract CTAs from 3 separate sources, then merge
    
    # 1) Nav links: header nav a
    nav_ctas: List[Dict[str, Any]] = []
    nav_elements = soup.select("header nav a, nav a")[:20]
    for el in nav_elements:
        label = _text(el) or ""
        href = el.get("href") or ""
        if not label and not href:
            continue
        
        in_nav, in_footer = _is_in_nav_or_footer(el)
        tag_name = el.name or ""
        role = el.get("role")
        type_attr = el.get("type")
        class_name = " ".join(el.get("class", [])) if el.get("class") else ""
        
        nav_ctas.append({
            "label": label[:80],
            "text": label[:80],
            "href": href,
            "kind": "link",
            "location": "above_fold",  # Nav is typically above fold
            "bucket": "nav",  # Explicitly nav
            "type": "secondary",
            "where": {
                "section": "nav",
                "selector": el.name,
                "bbox": [0, 0, 0, 0]
            },
            "notes": ""
        })
    
    # 2) Action candidates: button, a[role=button], input[type=submit], a.btn, a.cta, a.button
    action_ctas: List[Dict[str, Any]] = []
    # Select action candidates - use broader selectors and filter by class
    action_elements = []
    
    # Get all buttons and submit inputs
    action_elements.extend(soup.select("button")[:20])
    action_elements.extend(soup.select("input[type='submit'], input[type='button']")[:20])
    action_elements.extend(soup.select("a[role='button']")[:20])
    
    # Get all links and filter by class/attributes
    all_links = soup.select("a")[:50]
    for link in all_links:
        class_name = " ".join(link.get("class", [])) if link.get("class") else ""
        role = link.get("role", "")
        # Check if it matches action patterns
        if (role == "button" or 
            ACTION_CLASS_RE.search(class_name) or
            "btn" in class_name.lower() or
            "cta" in class_name.lower() or
            "button" in class_name.lower()):
            action_elements.append(link)
    
    # Remove duplicates (same element might match multiple selectors)
    seen_elements = set()
    unique_action_elements = []
    for el in action_elements:
        el_id = id(el)
        if el_id not in seen_elements:
            seen_elements.add(el_id)
            unique_action_elements.append(el)
    
    for el in unique_action_elements[:30]:
        label = _text(el) or (el.get("value") or "")
        href = el.get("href") or ""
        
        if not label and not href:
            continue
        
        # Skip if already in nav (don't double-count)
        in_nav, in_footer = _is_in_nav_or_footer(el)
        if in_nav:
            continue  # Already captured as nav
        
        # Determine kind
        kind = "unknown"
        if el.name == "button" or (el.name == "input" and el.get("type") in ["submit", "button"]):
            kind = "button"
        elif el.name == "a":
            kind = "link"
        elif el.name == "input" and el.get("type") == "submit":
            kind = "form_submit"
        
        tag_name = el.name or ""
        role = el.get("role")
        type_attr = el.get("type")
        class_name = " ".join(el.get("class", [])) if el.get("class") else ""
        text = label  # Use label as text for bucket determination
        
        bucket = bucket_for_element(
            tag_name=tag_name, role=role, type_attr=type_attr, class_name=class_name,
            text=text, in_nav=in_nav, in_footer=in_footer
        )
        
        action_ctas.append({
            "label": label[:80],
            "text": label[:80],
            "href": href,
            "kind": kind,
            "location": "above_fold" if len(action_ctas) < 3 else "below_fold",
            "bucket": bucket,
            "type": "primary" if len(action_ctas) == 0 else "secondary",
            "where": {
                "section": "hero" if len(action_ctas) == 0 else "unknown",
                "selector": el.name,
                "bbox": [0, 0, 0, 0]
            },
            "notes": ""
        })
    
    # 3) Content links: main a (excluding nav/footer)
    content_ctas: List[Dict[str, Any]] = []
    # Get all links in main, then filter out nav/footer
    main_elements = soup.select("main a")[:30]
    for el in main_elements:
        in_nav, in_footer = _is_in_nav_or_footer(el)
        # Skip if in nav or footer
        if in_nav or in_footer:
            continue
        
        label = _text(el) or ""
        href = el.get("href") or ""
        if not label and not href:
            continue
        
        # Skip if already captured as action (has action classes)
        class_name = " ".join(el.get("class", [])) if el.get("class") else ""
        role = el.get("role")
        type_attr = el.get("type")
        tag_name = el.name or ""
        
        # Use bucket_for_element to determine bucket (may be "action" if text matches)
        bucket = bucket_for_element(
            tag_name=tag_name, role=role, type_attr=type_attr, class_name=class_name,
            text=label, in_nav=in_nav, in_footer=in_footer
        )
        
        # Skip if determined to be action (should be captured in action_ctas section)
        if bucket == "action":
            continue  # Already captured as action
        
        content_ctas.append({
            "label": label[:80],
            "text": label[:80],
            "href": href,
            "kind": "link",
            "location": "above_fold" if len(content_ctas) < 3 else "below_fold",
            "bucket": bucket,
            "type": "secondary",
            "where": {
                "section": "main",
                "selector": el.name,
                "bbox": [0, 0, 0, 0]
            },
            "notes": ""
        })
    
    # 4) Footer links: footer a (excluding nav)
    footer_ctas: List[Dict[str, Any]] = []
    footer_elements = soup.select("footer a")[:20]
    for el in footer_elements:
        in_nav, in_footer = _is_in_nav_or_footer(el)
        # Skip if in nav (shouldn't happen, but safety check)
        if in_nav:
            continue
        
        label = _text(el) or ""
        href = el.get("href") or ""
        if not label and not href:
            continue
        
        # Use bucket_for_element to determine bucket (may be "action" if text matches)
        class_name = " ".join(el.get("class", [])) if el.get("class") else ""
        role = el.get("role")
        type_attr = el.get("type")
        tag_name = el.name or ""
        
        bucket = bucket_for_element(
            tag_name=tag_name, role=role, type_attr=type_attr, class_name=class_name,
            text=label, in_nav=in_nav, in_footer=in_footer
        )
        
        # Skip if determined to be action (should be captured in action_ctas section)
        if bucket == "action":
            continue  # Already captured as action
        
        footer_ctas.append({
            "label": label[:80],
            "text": label[:80],
            "href": href,
            "kind": "link",
            "location": "below_fold",  # Footer is always below fold
            "bucket": bucket,
            "type": "secondary",
            "where": {
                "section": "footer",
                "selector": el.name,
                "bbox": [0, 0, 0, 0]
            },
            "notes": ""
        })
    
    # Merge all CTAs (nav first, then action, then content, then footer)
    # Remove duplicates based on text+href combination
    seen_ctas = set()
    ctas: List[Dict[str, Any]] = []
    
    for cta_list in [nav_ctas, action_ctas, content_ctas, footer_ctas]:
        for cta in cta_list:
            # Create unique key from text and href
            cta_key = (cta.get("text", "").lower().strip(), cta.get("href", "").lower().strip())
            if cta_key not in seen_ctas and (cta_key[0] or cta_key[1]):  # At least one must be non-empty
                seen_ctas.add(cta_key)
                ctas.append(cta)
    
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
        },
        "hero_headline": hero_headline,
        "subheadline": subheadline
    }

