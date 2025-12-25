"""
Text extractor: converts text input into PageMap schema using LLM.
"""
import logging
import json
import os
from typing import Dict, Any
from api.schemas.page_map import PageMap, PrimaryCTA, Offer, VisualHierarchy
from openai import OpenAI

logger = logging.getLogger(__name__)


def _get_openai_client() -> OpenAI:
    """Get OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)


async def extract_from_text(text: str, goal: str) -> PageMap:
    """
    Extract PageMap from text using LLM.
    
    Args:
        text: Text content to analyze
        goal: Analysis goal (leads, sales, etc.)
        
    Returns:
        PageMap instance
        
    Raises:
        Exception: If extraction fails
    """
    # Build prompt for structured extraction
    system_prompt = """You are a page analysis expert. Extract structured information from this landing page text.

Return ONLY valid JSON matching this exact schema:
{
  "headline": "string or null",
  "subheadline": "string or null",
  "primary_cta": {"text": "string or null", "intent": "string or null"},
  "secondary_ctas": [{"text": "string", "href": "string or null"}],
  "offer": {"type": "string or null", "value": "string or null", "price_info": "string or null"},
  "trust_signals": ["string"],
  "risk_signals": ["string"],
  "friction_signals": ["string"],
  "visual_hierarchy": {"focus": "string or null", "cta_visibility": 0.0-1.0 or null, "noise": 0.0-1.0 or null},
  "copy_snippets": ["string"],
  "page_type": "string or null",
  "language": "string or null"
}

Extract:
- headline: Main H1 or hero title text
- subheadline: H2 or subtitle below headline
- primary_cta: Main call-to-action button/link text and intent (signup, purchase, contact, etc.)
- secondary_ctas: Other CTAs as array
- offer: Pricing, discount, trial info if mentioned
- trust_signals: Keywords/phrases indicating trust (testimonials, guarantees, security badges, etc.)
- risk_signals: Keywords/phrases indicating risk or concerns
- friction_signals: Elements that create friction (forms, long text, etc.)
- visual_hierarchy: Visual focus element (inferred from text structure), CTA visibility (0-1), noise/clutter (0-1)
- copy_snippets: Key copy snippets (max 3, each <200 chars)
- page_type: ecommerce_product, saas_home, personal_brand_consultant, b2b_corporate_service, etc.
- language: Detected language code (en, fa, etc.)

Return ONLY the JSON object, no markdown, no explanation."""

    user_prompt = f"Extract all page information from this text:\n\n{text[:4000]}"  # Limit text length

    try:
        client = _get_openai_client()
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}  # Force JSON mode
        )
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")
        
        # Parse JSON
        data = json.loads(content)
        
        # Build PageMap
        primary_cta_data = data.get("primary_cta", {})
        primary_cta = None
        if primary_cta_data and primary_cta_data.get("text"):
            primary_cta = PrimaryCTA(
                text=primary_cta_data.get("text"),
                intent=primary_cta_data.get("intent"),
                clarity=None
            )
        
        offer_data = data.get("offer", {})
        offer = None
        if offer_data and (offer_data.get("type") or offer_data.get("value")):
            offer = Offer(
                type=offer_data.get("type"),
                value=offer_data.get("value"),
                price_info=offer_data.get("price_info")
            )
        
        visual_hierarchy_data = data.get("visual_hierarchy", {})
        visual_hierarchy = None
        if visual_hierarchy_data:
            visual_hierarchy = VisualHierarchy(
                focus=visual_hierarchy_data.get("focus"),
                cta_visibility=visual_hierarchy_data.get("cta_visibility"),
                noise=visual_hierarchy_data.get("noise")
            )
        
        return PageMap(
            source="text",
            goal=goal,
            page_type=data.get("page_type"),
            headline=data.get("headline"),
            subheadline=data.get("subheadline"),
            primary_cta=primary_cta,
            secondary_ctas=data.get("secondary_ctas", []),
            offer=offer,
            trust_signals=data.get("trust_signals", []),
            risk_signals=data.get("risk_signals", []),
            friction_signals=data.get("friction_signals", []),
            visual_hierarchy=visual_hierarchy,
            copy_snippets=data.get("copy_snippets", []),
            language=data.get("language", "en")
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OpenAI JSON: {e}")
        raise ValueError(f"Invalid JSON from LLM: {e}")
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        raise ValueError(f"Text extraction failed: {str(e)}")

