"""
URL extractor: converts URL input into PageMap schema.
"""
import logging
from typing import Dict, Any
from api.schemas.page_map import PageMap, PrimaryCTA, Offer, VisualHierarchy
from api.services.page_capture import capture_page_artifacts
from api.services.page_extract import extract_page_map
from api.brain.context.page_type import detect_page_type
from api.brain.context.brand_context import detect_brand_context

logger = logging.getLogger(__name__)


async def extract_from_url(url: str, goal: str) -> PageMap:
    """
    Extract PageMap from URL.
    
    Args:
        url: URL to analyze
        goal: Analysis goal (leads, sales, etc.)
        
    Returns:
        PageMap instance
        
    Raises:
        Exception: If extraction fails
    """
    # 1. Capture page artifacts
    capture = await capture_page_artifacts(url)
    if not capture:
        raise ValueError("Failed to capture page artifacts")
    
    # 2. Extract page map (legacy format)
    page_map_dict = extract_page_map(capture)
    
    # 3. Extract headlines
    headlines = page_map_dict.get("headlines", [])
    headline = None
    subheadline = None
    if headlines:
        h1_list = [h for h in headlines if h.get("tag") == "h1"]
        h2_list = [h for h in headlines if h.get("tag") == "h2"]
        if h1_list:
            headline = h1_list[0].get("text")
        if h2_list:
            subheadline = h2_list[0].get("text")
    
    # 4. Extract CTAs
    ctas = page_map_dict.get("ctas", [])
    primary_cta = None
    secondary_ctas = []
    
    if ctas:
        primary = ctas[0] if ctas else None
        if primary:
            primary_cta = PrimaryCTA(
                text=primary.get("label"),
                intent=None,  # Will be inferred later
                clarity=None  # Will be calculated later
            )
        
        # Secondary CTAs
        for cta in ctas[1:6]:  # Limit to 5 secondary CTAs
            secondary_ctas.append({
                "text": cta.get("label"),
                "href": cta.get("href"),
                "type": cta.get("type", "secondary")
            })
    
    # 5. Extract trust signals
    trust_signals_raw = page_map_dict.get("trust_signals", [])
    trust_signals = []
    for ts in trust_signals_raw:
        if isinstance(ts, dict):
            trust_signals.append(ts.get("text_or_label", ""))
        elif isinstance(ts, str):
            trust_signals.append(ts)
    
    # 6. Detect page type
    dom = capture.get("dom", {})
    page_text = dom.get("readable_text_excerpt", "") or dom.get("html_excerpt", "") or ""
    page_type_result = detect_page_type(
        url=url,
        page_text=page_text,
        page_map=page_map_dict,
        intent=None,
        brand_ctx={}
    )
    page_type = page_type_result.type if page_type_result else None
    
    # 7. Extract copy snippets
    copy_snippets = []
    if page_text:
        # Take first 500 chars as snippet
        copy_snippets.append(page_text[:500])
    
    # 8. Build PageMap
    return PageMap(
        source="url",
        goal=goal,
        page_type=page_type,
        headline=headline,
        subheadline=subheadline,
        primary_cta=primary_cta,
        secondary_ctas=secondary_ctas,
        offer=None,  # Will be extracted by decision engine
        trust_signals=trust_signals,
        risk_signals=[],  # Will be detected by decision engine
        friction_signals=[],  # Will be detected by decision engine
        visual_hierarchy=None,  # Will be extracted by visual analysis
        copy_snippets=copy_snippets,
        language="en"  # Default, can be detected later
    )

