"""
Decision Signal Detection Engine (v1)
Detects 12 key decision signals from page content and structure.
Always returns 12 signals with consistent schema.
"""
import os
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load .env
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

# Signal definitions (12 signals with categories)
SIGNAL_DEFINITIONS = [
    # CLARITY (3 signals)
    {"id": "value_prop_presence", "label": "Value Proposition Presence", "category": "clarity"},
    {"id": "value_prop_specificity", "label": "Value Proposition Specificity", "category": "clarity"},
    {"id": "information_hierarchy", "label": "Information Hierarchy", "category": "clarity"},
    # ACTION (3 signals)
    {"id": "primary_cta_presence", "label": "Primary CTA Presence", "category": "action"},
    {"id": "cta_clarity", "label": "CTA Clarity", "category": "action"},
    {"id": "cta_competition", "label": "CTA Competition", "category": "action"},
    # TRUST (3 signals)
    {"id": "social_proof_presence", "label": "Social Proof Presence", "category": "trust"},
    {"id": "risk_reducers", "label": "Risk Reducers", "category": "trust"},
    {"id": "legitimacy_signals", "label": "Legitimacy Signals", "category": "trust"},
    # FRICTION (3 signals)
    {"id": "pricing_visibility", "label": "Pricing Visibility", "category": "friction"},
    {"id": "form_friction", "label": "Form Friction", "category": "friction"},
    {"id": "cognitive_load", "label": "Cognitive Load", "category": "friction"},
]

# Category weights (for internal use only)
CATEGORY_WEIGHTS = {
    "clarity": 0.35,
    "action": 0.25,
    "trust": 0.25,
    "friction": 0.15,
}

# CTA action keywords
CTA_ACTION_KEYWORDS = [
    "start", "get", "try", "request", "book", "analyze", "buy", "order",
    "sign up", "register", "subscribe", "download", "learn more", "get started"
]

# Value proposition keywords (audience + outcome + problem solved)
VALUE_PROP_KEYWORDS = ["help", "analyze", "improve", "grow", "reduce", "increase"]

# Vague language red flags
VAGUE_RED_FLAGS = ["best", "powerful", "next-gen", "ultimate", "revolutionary", "amazing"]

# Social proof keywords
SOCIAL_PROOF_KEYWORDS = [
    "trusted by", "customers", "reviews", "testimonials", "logos",
    "clients", "users", "satisfied", "recommended", "featured in"
]

# Risk reducer keywords
RISK_REDUCER_KEYWORDS = [
    "free trial", "cancel anytime", "no credit card", "money-back",
    "guarantee", "refund", "no commitment", "try free"
]

# Legitimacy keywords
LEGITIMACY_KEYWORDS = [
    "about", "contact", "address", "privacy", "terms", "support",
    "help", "faq", "email", "phone"
]

# Pricing keywords
PRICING_KEYWORDS = [
    "pricing", "plans", "price", "cost", "$", "€", "£", "trial",
    "subscription", "monthly", "yearly", "per month", "per year"
]

# Bad CTA examples (vague)
BAD_CTA_EXAMPLES = ["submit", "click here", "read more", "continue", "next"]


def _normalize_text(text: str) -> str:
    """Normalize text for keyword matching."""
    if not text:
        return ""
    return text.lower().strip()


def _count_keywords(text: str, keywords: List[str]) -> int:
    """Count how many keywords appear in text."""
    normalized = _normalize_text(text)
    count = 0
    for keyword in keywords:
        if keyword in normalized:
            count += 1
    return count


def _find_keywords_in_text(text: str, keywords: List[str]) -> List[str]:
    """Find which keywords appear in text."""
    normalized = _normalize_text(text)
    found = []
    for keyword in keywords:
        if keyword in normalized:
            found.append(keyword)
    return found


def _get_hero_text(page_text: str, headlines: List[Dict[str, Any]]) -> str:
    """Extract hero section text (first 500 chars + H1)."""
    hero_parts = []
    
    # Get H1 if exists
    for h in headlines:
        if h.get("tag") == "h1":
            hero_parts.append(h.get("text", ""))
            break
    
    # Add first 500 chars of page text
    hero_parts.append(page_text[:500] if page_text else "")
    
    return " ".join(hero_parts)


def _detect_value_prop_presence(page_text: str, headlines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect value proposition presence (CLARITY)."""
    hero_text = _get_hero_text(page_text, headlines)
    
    # Check for at least 2 of: audience + outcome + problem solved
    value_prop_count = _count_keywords(hero_text, VALUE_PROP_KEYWORDS)
    found_keywords = _find_keywords_in_text(hero_text, VALUE_PROP_KEYWORDS)
    
    # Check if there's a clear sentence (has subject + verb + object structure)
    has_clear_sentence = len(hero_text.split(".")) > 0 and len(hero_text) > 50
    
    if value_prop_count >= 2 and has_clear_sentence:
        return {
            "id": "value_prop_presence",
            "label": "Value Proposition Presence",
            "category": "clarity",
            "status": "present",
            "confidence": 0.9,
            "reason": f"Clear value proposition found with {value_prop_count} value indicators",
            "recommendation": "Value proposition is clearly stated",
            "evidence": {
                "keywords": found_keywords,
                "location": "hero"
            }
        }
    elif value_prop_count >= 1 or has_clear_sentence:
        return {
            "id": "value_prop_presence",
            "label": "Value Proposition Presence",
            "category": "clarity",
            "status": "weak",
            "confidence": 0.6,
            "reason": "Value proposition exists but is too generic",
            "recommendation": "Make value proposition more specific: who it helps, what outcome, what problem solved",
            "evidence": {
                "keywords": found_keywords if found_keywords else None,
                "location": "hero"
            }
        }
    else:
        return {
            "id": "value_prop_presence",
            "label": "Value Proposition Presence",
            "category": "clarity",
            "status": "missing",
            "confidence": 0.8,
            "reason": "No clear value proposition detected in hero section",
            "recommendation": "Add a clear value proposition: who you help, what outcome, what problem solved",
            "evidence": {
                "location": "hero"
            }
        }


async def _detect_value_prop_specificity(page_text: str, headlines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect value proposition specificity using LLM (CLARITY)."""
    hero_text = _get_hero_text(page_text, headlines)
    
    if not hero_text or len(hero_text) < 20:
        return {
            "id": "value_prop_specificity",
            "label": "Value Proposition Specificity",
            "category": "clarity",
            "status": "unclear",
            "confidence": 0.3,
            "reason": "Insufficient visible evidence in the provided content.",
            "recommendation": "Add specific numbers, results, or concrete details to value proposition"
        }
    
    # Check for vague red flags
    vague_count = _count_keywords(hero_text, VAGUE_RED_FLAGS)
    has_numbers = bool(re.search(r'\d+', hero_text))
    
    try:
        from ..chat import get_client
        
        client = get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a copywriting expert. Analyze if the value proposition is specific (with numbers, results, concrete details) or vague (using words like 'best', 'powerful', 'ultimate' without specifics). Return JSON only: {\"status\": \"specific|vague|mixed\", \"confidence\": 0.0-1.0, \"reason\": \"brief explanation\", \"recommendation\": \"actionable advice\"}"
                },
                {
                    "role": "user",
                    "content": f"Hero text: {hero_text[:400]}\n\nIs the value proposition specific or vague? Return JSON only."
                }
            ],
            temperature=0.3,
            max_tokens=200,
        )
        
        import json
        raw_json = response.choices[0].message.content or "{}"
        if "```json" in raw_json:
            raw_json = raw_json.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_json:
            raw_json = raw_json.split("```")[1].split("```")[0].strip()
        
        data = json.loads(raw_json)
        
        return {
            "id": "value_prop_specificity",
            "label": "Value Proposition Specificity",
            "category": "clarity",
            "status": data.get("status", "mixed"),
            "confidence": float(data.get("confidence", 0.5)),
            "reason": data.get("reason", "LLM analysis completed"),
            "recommendation": data.get("recommendation", "Use specific numbers, results, and concrete details instead of vague claims"),
            "evidence": {
                "text": hero_text[:200] if hero_text else None,
                "keywords": _find_keywords_in_text(hero_text, VAGUE_RED_FLAGS) if vague_count > 0 else None
            }
        }
    except Exception as e:
        # Fallback to rule-based if LLM fails
        if vague_count >= 2 and not has_numbers:
            status = "vague"
            confidence = 0.8
        elif vague_count >= 1:
            status = "mixed"
            confidence = 0.6
        else:
            status = "specific" if has_numbers else "mixed"
            confidence = 0.7
        
        return {
            "id": "value_prop_specificity",
            "label": "Value Proposition Specificity",
            "category": "clarity",
            "status": status,
            "confidence": confidence,
            "reason": f"Found {vague_count} vague terms, {'has' if has_numbers else 'no'} numbers",
            "recommendation": "Use specific numbers, results, and concrete details instead of vague claims",
            "evidence": {
                "keywords": _find_keywords_in_text(hero_text, VAGUE_RED_FLAGS) if vague_count > 0 else None
            }
        }


def _detect_information_hierarchy(headlines: List[Dict[str, Any]], ctas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect information hierarchy: H1 → supporting text → CTA (CLARITY)."""
    h1_exists = any(h.get("tag") == "h1" for h in headlines)
    h2_exists = any(h.get("tag") == "h2" for h in headlines)
    cta_exists = len(ctas) > 0
    
    # Check if hierarchy is clear: H1 → supporting text → CTA
    if h1_exists and cta_exists:
        return {
            "id": "information_hierarchy",
            "label": "Information Hierarchy",
            "category": "clarity",
            "status": "present",
            "confidence": 0.9 if h2_exists else 0.8,
            "reason": f"H1 present, {len(headlines)} headline(s), {len(ctas)} CTA(s) - clear hierarchy",
            "recommendation": "Information hierarchy is clear: H1 → supporting text → CTA",
            "evidence": {
                "location": "hero"
            }
        }
    elif h1_exists or cta_exists:
        return {
            "id": "information_hierarchy",
            "label": "Information Hierarchy",
            "category": "clarity",
            "status": "weak",
            "confidence": 0.6,
            "reason": f"{'H1' if h1_exists else 'No H1'}, {len(ctas)} CTA(s) - incomplete hierarchy",
            "recommendation": "Ensure clear hierarchy: H1 → supporting text → CTA",
            "evidence": {
                "location": "hero"
            }
        }
    else:
        return {
            "id": "information_hierarchy",
            "label": "Information Hierarchy",
            "category": "clarity",
            "status": "missing",
            "confidence": 0.8,
            "reason": "No clear H1 or CTA detected - users may not know what to read first",
            "recommendation": "Add H1 headline and clear CTA to establish information hierarchy",
            "evidence": {
                "location": "hero"
            }
        }


def _detect_primary_cta_presence(page_text: str, ctas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect primary CTA presence (ACTION)."""
    # Check CTAs from page_map
    action_ctas = []
    for cta in ctas:
        cta_text = _normalize_text(cta.get("label", ""))
        if any(keyword in cta_text for keyword in CTA_ACTION_KEYWORDS):
            action_ctas.append(cta)
    
    # Check text for CTA keywords
    cta_keyword_count = _count_keywords(page_text, CTA_ACTION_KEYWORDS)
    found_keywords = _find_keywords_in_text(page_text, CTA_ACTION_KEYWORDS)
    
    if len(action_ctas) > 0:
        return {
            "id": "primary_cta_presence",
            "label": "Primary CTA Presence",
            "category": "action",
            "status": "present",
            "confidence": 0.9,
            "reason": f"Found {len(action_ctas)} action-oriented CTA(s)",
            "recommendation": "Primary CTA is present and action-oriented",
            "evidence": {
                "keywords": found_keywords[:5] if found_keywords else None,
                "location": "hero"
            }
        }
    elif cta_keyword_count >= 2:
        return {
            "id": "primary_cta_presence",
            "label": "Primary CTA Presence",
            "category": "action",
            "status": "weak",
            "confidence": 0.6,
            "reason": f"Found {cta_keyword_count} CTA keywords but no clear CTA button",
            "recommendation": "Add a prominent action-oriented CTA button (e.g., 'Get Started', 'Try Now')",
            "evidence": {
                "keywords": found_keywords[:5] if found_keywords else None
            }
        }
    else:
        return {
            "id": "primary_cta_presence",
            "label": "Primary CTA Presence",
            "category": "action",
            "status": "missing",
            "confidence": 0.8,
            "reason": "No action-oriented CTA detected",
            "recommendation": "Add a clear primary CTA with action verbs (start, get, try, request, book)",
            "evidence": {}
        }


def _detect_cta_clarity(ctas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect CTA clarity: does it say the outcome? (ACTION)."""
    if len(ctas) == 0:
        return {
            "id": "cta_clarity",
            "label": "CTA Clarity",
            "category": "action",
            "status": "unclear",
            "confidence": 0.3,
            "reason": "Insufficient visible evidence in the provided content.",
            "recommendation": "Add a clear CTA that states the outcome (e.g., 'Get Report', 'Start Analysis')"
        }
    
    # Check each CTA
    clear_ctas = []
    vague_ctas = []
    
    for cta in ctas:
        cta_text = _normalize_text(cta.get("label", ""))
        is_bad = any(bad in cta_text for bad in BAD_CTA_EXAMPLES)
        has_outcome = any(keyword in cta_text for keyword in ["get", "start", "try", "analyze", "report", "result"])
        
        if is_bad:
            vague_ctas.append(cta_text)
        elif has_outcome:
            clear_ctas.append(cta_text)
        else:
            vague_ctas.append(cta_text)
    
    if len(clear_ctas) > 0 and len(vague_ctas) == 0:
        return {
            "id": "cta_clarity",
            "label": "CTA Clarity",
            "category": "action",
            "status": "present",
            "confidence": 0.9,
            "reason": f"All {len(clear_ctas)} CTA(s) clearly state the outcome",
            "recommendation": "CTAs are clear and outcome-focused",
            "evidence": {
                "text": clear_ctas[0] if clear_ctas else None
            }
        }
    elif len(clear_ctas) > 0:
        return {
            "id": "cta_clarity",
            "label": "CTA Clarity",
            "category": "action",
            "status": "weak",
            "confidence": 0.6,
            "reason": f"{len(clear_ctas)} clear CTA(s) but {len(vague_ctas)} vague CTA(s) found",
            "recommendation": "Make all CTAs outcome-focused (e.g., 'Get Report' not 'Submit')",
            "evidence": {
                "text": vague_ctas[0] if vague_ctas else None
            }
        }
    else:
        return {
            "id": "cta_clarity",
            "label": "CTA Clarity",
            "category": "action",
            "status": "missing",
            "confidence": 0.8,
            "reason": f"All {len(vague_ctas)} CTA(s) are vague (e.g., 'Submit', 'Click Here')",
            "recommendation": "Replace vague CTAs with outcome-focused ones (e.g., 'Get Report', 'Start Analysis')",
            "evidence": {
                "text": vague_ctas[0] if vague_ctas else None
            }
        }


def _detect_cta_competition(ctas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect CTA competition: multiple CTAs at same level (ACTION)."""
    if len(ctas) == 0:
        return {
            "id": "cta_competition",
            "label": "CTA Competition",
            "category": "action",
            "status": "unclear",
            "confidence": 0.3,
            "reason": "Insufficient visible evidence in the provided content.",
            "recommendation": "Add at least one primary CTA"
        }
    
    # Count primary CTAs (first few are usually primary)
    primary_count = min(len(ctas), 3)  # First 3 are likely in hero
    total_count = len(ctas)
    
    if total_count == 1:
        return {
            "id": "cta_competition",
            "label": "CTA Competition",
            "category": "action",
            "status": "present",
            "confidence": 0.9,
            "reason": "Single CTA - no competition, clear focus",
            "recommendation": "Single CTA is optimal for conversion",
            "evidence": {
                "location": "hero"
            }
        }
    elif primary_count <= 2:
        return {
            "id": "cta_competition",
            "label": "CTA Competition",
            "category": "action",
            "status": "weak",
            "confidence": 0.7,
            "reason": f"{primary_count} CTA(s) in hero - moderate competition",
            "recommendation": "Consider reducing to 1 primary CTA for better focus",
            "evidence": {
                "location": "hero"
            }
        }
    else:
        return {
            "id": "cta_competition",
            "label": "CTA Competition",
            "category": "action",
            "status": "missing",
            "confidence": 0.8,
            "reason": f"{total_count} CTA(s) found - high competition, unclear focus",
            "recommendation": "Too many CTAs confuse users. Focus on 1 primary action",
            "evidence": {
                "location": "hero"
            }
        }


def _detect_social_proof_presence(page_text: str) -> Dict[str, Any]:
    """Detect social proof presence (TRUST)."""
    social_count = _count_keywords(page_text, SOCIAL_PROOF_KEYWORDS)
    found_keywords = _find_keywords_in_text(page_text, SOCIAL_PROOF_KEYWORDS)
    
    if social_count >= 3:
        return {
            "id": "social_proof_presence",
            "label": "Social Proof Presence",
            "category": "trust",
            "status": "present",
            "confidence": 0.9,
            "reason": f"Found {social_count} social proof indicators",
            "recommendation": "Strong social proof signals present",
            "evidence": {
                "keywords": found_keywords[:5] if found_keywords else None
            }
        }
    elif social_count >= 1:
        return {
            "id": "social_proof_presence",
            "label": "Social Proof Presence",
            "category": "trust",
            "status": "weak",
            "confidence": 0.6,
            "reason": f"Only {social_count} social proof indicator(s) found",
            "recommendation": "Add testimonials, reviews, customer logos, or 'trusted by' section",
            "evidence": {
                "keywords": found_keywords[:5] if found_keywords else None
            }
        }
    else:
        return {
            "id": "social_proof_presence",
            "label": "Social Proof Presence",
            "category": "trust",
            "status": "missing",
            "confidence": 0.8,
            "reason": "No social proof detected",
            "recommendation": "Add testimonials, reviews, customer logos, or 'trusted by' section",
            "evidence": {}
        }


def _detect_risk_reducers(page_text: str) -> Dict[str, Any]:
    """Detect risk reducers (TRUST)."""
    risk_count = _count_keywords(page_text, RISK_REDUCER_KEYWORDS)
    found_keywords = _find_keywords_in_text(page_text, RISK_REDUCER_KEYWORDS)
    
    if risk_count >= 2:
        return {
            "id": "risk_reducers",
            "label": "Risk Reducers",
            "category": "trust",
            "status": "present",
            "confidence": 0.9,
            "reason": f"Found {risk_count} risk reduction signals",
            "recommendation": "Strong risk reduction signals present",
            "evidence": {
                "keywords": found_keywords[:5] if found_keywords else None
            }
        }
    elif risk_count >= 1:
        return {
            "id": "risk_reducers",
            "label": "Risk Reducers",
            "category": "trust",
            "status": "weak",
            "confidence": 0.6,
            "reason": f"Only {risk_count} risk reducer(s) found",
            "recommendation": "Add free trial, money-back guarantee, or 'cancel anytime' messaging",
            "evidence": {
                "keywords": found_keywords[:5] if found_keywords else None
            }
        }
    else:
        return {
            "id": "risk_reducers",
            "label": "Risk Reducers",
            "category": "trust",
            "status": "missing",
            "confidence": 0.8,
            "reason": "No risk reduction signals detected",
            "recommendation": "Add free trial, money-back guarantee, or 'cancel anytime' messaging",
            "evidence": {}
        }


def _detect_legitimacy_signals(page_text: str) -> Dict[str, Any]:
    """Detect legitimacy signals (TRUST)."""
    legitimacy_count = _count_keywords(page_text, LEGITIMACY_KEYWORDS)
    found_keywords = _find_keywords_in_text(page_text, LEGITIMACY_KEYWORDS)
    
    if legitimacy_count >= 3:
        return {
            "id": "legitimacy_signals",
            "label": "Legitimacy Signals",
            "category": "trust",
            "status": "present",
            "confidence": 0.9,
            "reason": f"Found {legitimacy_count} legitimacy indicators (contact, about, privacy, terms)",
            "recommendation": "Legitimacy signals are present",
            "evidence": {
                "keywords": found_keywords[:5] if found_keywords else None
            }
        }
    elif legitimacy_count >= 1:
        return {
            "id": "legitimacy_signals",
            "label": "Legitimacy Signals",
            "category": "trust",
            "status": "weak",
            "confidence": 0.6,
            "reason": f"Only {legitimacy_count} legitimacy indicator(s) found",
            "recommendation": "Add contact information, about page, privacy policy, and terms of service",
            "evidence": {
                "keywords": found_keywords[:5] if found_keywords else None
            }
        }
    else:
        return {
            "id": "legitimacy_signals",
            "label": "Legitimacy Signals",
            "category": "trust",
            "status": "missing",
            "confidence": 0.8,
            "reason": "No legitimacy signals detected (contact, about, privacy, terms)",
            "recommendation": "Add contact information, about page, privacy policy, and terms of service",
            "evidence": {}
        }


def _detect_pricing_visibility(page_text: str) -> Dict[str, Any]:
    """Detect pricing visibility (FRICTION)."""
    pricing_count = _count_keywords(page_text, PRICING_KEYWORDS)
    found_keywords = _find_keywords_in_text(page_text, PRICING_KEYWORDS)
    
    if pricing_count >= 3:
        return {
            "id": "pricing_visibility",
            "label": "Pricing Visibility",
            "category": "friction",
            "status": "present",
            "confidence": 0.9,
            "reason": f"Found {pricing_count} pricing-related keywords - pricing is visible",
            "recommendation": "Pricing is clearly visible",
            "evidence": {
                "keywords": found_keywords[:5] if found_keywords else None
            }
        }
    elif pricing_count >= 1:
        return {
            "id": "pricing_visibility",
            "label": "Pricing Visibility",
            "category": "friction",
            "status": "weak",
            "confidence": 0.6,
            "reason": f"Only {pricing_count} pricing keyword(s) found - pricing path may be unclear",
            "recommendation": "Make pricing more prominent and clear to reduce friction",
            "evidence": {
                "keywords": found_keywords[:5] if found_keywords else None
            }
        }
    else:
        return {
            "id": "pricing_visibility",
            "label": "Pricing Visibility",
            "category": "friction",
            "status": "missing",
            "confidence": 0.8,
            "reason": "No pricing information detected - unclear pricing path",
            "recommendation": "Add clear pricing information to reduce friction",
            "evidence": {}
        }


def _detect_form_friction(page_text: str, ctas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect form friction (FRICTION)."""
    # Look for form-related keywords
    form_keywords = ["form", "input", "field", "required", "submit", "register", "sign up", "email", "password"]
    form_count = _count_keywords(page_text, form_keywords)
    
    # Check if there are form CTAs
    form_ctas = [cta for cta in ctas if any(kw in _normalize_text(cta.get("label", "")) for kw in ["sign", "register", "submit"])]
    
    # Check if form appears before value is understood (heuristic: form keywords in first 500 chars)
    early_form = form_count > 0 and len(page_text) > 0 and _count_keywords(page_text[:500], form_keywords) > 0
    
    if form_count >= 5 or (len(form_ctas) >= 2 and early_form):
        return {
            "id": "form_friction",
            "label": "Form Friction",
            "category": "friction",
            "status": "missing",
            "confidence": 0.8,
            "reason": f"Complex form detected ({form_count} form keywords) or form appears too early",
            "recommendation": "Simplify form or move it after value is communicated",
            "evidence": {
                "keywords": _find_keywords_in_text(page_text, form_keywords)[:5] if form_count > 0 else None
            }
        }
    elif form_count >= 2:
        return {
            "id": "form_friction",
            "label": "Form Friction",
            "category": "friction",
            "status": "weak",
            "confidence": 0.6,
            "reason": f"Moderate form complexity ({form_count} form keywords)",
            "recommendation": "Keep forms simple and only ask for essential information",
            "evidence": {
                "keywords": _find_keywords_in_text(page_text, form_keywords)[:5] if form_count > 0 else None
            }
        }
    else:
        return {
            "id": "form_friction",
            "label": "Form Friction",
            "category": "friction",
            "status": "present",
            "confidence": 0.7,
            "reason": "Minimal form elements detected - low friction",
            "recommendation": "Forms appear simple - good for conversion",
            "evidence": {}
        }


async def _detect_cognitive_load(page_text: str, headlines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect cognitive load (FRICTION)."""
    if not page_text or len(page_text) < 50:
        return {
            "id": "cognitive_load",
            "label": "Cognitive Load",
            "category": "friction",
            "status": "unclear",
            "confidence": 0.3,
            "reason": "Insufficient visible evidence in the provided content.",
            "recommendation": "Ensure content is well-organized with clear headings"
        }
    
    # Count headlines
    h1_count = len([h for h in headlines if h.get("tag") == "h1"])
    h2_count = len([h for h in headlines if h.get("tag") == "h2"])
    
    # Estimate text length
    text_length = len(page_text)
    word_count = len(page_text.split())
    
    # Check for conflicting messages (heuristic: multiple CTAs with different actions)
    cta_keywords = ["buy", "try", "learn", "get", "start"]
    conflicting_actions = len(set([kw for kw in cta_keywords if kw in _normalize_text(page_text)]))
    
    try:
        from ..chat import get_client
        
        client = get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a UX expert. Analyze cognitive load: too much text, conflicting messages, unclear hierarchy. Return JSON only: {\"status\": \"low|moderate|high\", \"confidence\": 0.0-1.0, \"reason\": \"brief explanation\", \"recommendation\": \"actionable advice\"}"
                },
                {
                    "role": "user",
                    "content": f"H1 count: {h1_count}, H2 count: {h2_count}, Word count: ~{word_count}\n\nPage text (first 600 chars): {page_text[:600]}\n\nAssess cognitive load. Return JSON only."
                }
            ],
            temperature=0.3,
            max_tokens=200,
        )
        
        import json
        raw_json = response.choices[0].message.content or "{}"
        if "```json" in raw_json:
            raw_json = raw_json.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_json:
            raw_json = raw_json.split("```")[1].split("```")[0].strip()
        
        data = json.loads(raw_json)
        
        return {
            "id": "cognitive_load",
            "label": "Cognitive Load",
            "category": "friction",
            "status": data.get("status", "moderate"),
            "confidence": float(data.get("confidence", 0.5)),
            "reason": data.get("reason", "LLM analysis completed"),
            "recommendation": data.get("recommendation", "Reduce text, improve hierarchy, remove conflicting messages"),
            "evidence": {
                "text": page_text[:200] if page_text else None
            }
        }
    except Exception as e:
        # Fallback to rule-based
        if word_count > 1000 or conflicting_actions >= 3:
            status = "high"
            confidence = 0.8
        elif word_count > 500 or conflicting_actions >= 2:
            status = "moderate"
            confidence = 0.6
        else:
            status = "low"
            confidence = 0.7
        
        return {
            "id": "cognitive_load",
            "label": "Cognitive Load",
            "category": "friction",
            "status": status,
            "confidence": confidence,
            "reason": f"~{word_count} words, {h1_count} H1, {h2_count} H2, {conflicting_actions} conflicting actions",
            "recommendation": "Reduce text, improve hierarchy with clear H1/H2, remove conflicting messages",
            "evidence": {
                "text": page_text[:200] if page_text else None
            }
        }


def _calculate_summary(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate summary with primary and secondary issues."""
    # Find signals with status "missing" or "weak", sorted by category weight
    issues = []
    for signal in signals:
        if signal.get("status") in ["missing", "weak"]:
            category = signal.get("category", "friction")
            weight = CATEGORY_WEIGHTS.get(category, 0.15)
            issues.append({
                "id": signal.get("id"),
                "status": signal.get("status"),
                "confidence": signal.get("confidence", 0.5),
                "weight": weight,
                "category": category
            })
    
    # Sort by weight * (1 - confidence) to prioritize high-weight, low-confidence issues
    issues.sort(key=lambda x: x["weight"] * (1 - x["confidence"]), reverse=True)
    
    primary_issue = issues[0].get("id") if issues else None
    secondary_issue = issues[1].get("id") if len(issues) > 1 else None
    
    return {
        "primary_issue": primary_issue,
        "secondary_issue": secondary_issue
    }


async def detect_signals(
    capture: Dict[str, Any],
    page_map: Dict[str, Any],
    goal: Optional[str] = None,
    locale: Optional[str] = None
) -> Dict[str, Any]:
    """
    Detect 12 decision signals from page content.
    
    Args:
        capture: Dictionary from capture_page_artifacts()
        page_map: Dictionary from extract_page_map()
        goal: Optional goal (leads, sales, etc.)
        locale: Optional locale (fa, en, etc.)
        
    Returns:
        Dictionary with "signals" (12 items) and "summary"
    """
    # Extract data
    dom = capture.get("dom", {})
    page_text = dom.get("readable_text_excerpt", "") or dom.get("html_excerpt", "") or ""
    headlines = page_map.get("headlines", [])
    ctas = page_map.get("ctas", [])
    
    # Detect all signals
    signals = []
    
    # CLARITY (3 signals)
    signals.append(_detect_value_prop_presence(page_text, headlines))
    signals.append(await _detect_value_prop_specificity(page_text, headlines))
    signals.append(_detect_information_hierarchy(headlines, ctas))
    
    # ACTION (3 signals)
    signals.append(_detect_primary_cta_presence(page_text, ctas))
    signals.append(_detect_cta_clarity(ctas))
    signals.append(_detect_cta_competition(ctas))
    
    # TRUST (3 signals)
    signals.append(_detect_social_proof_presence(page_text))
    signals.append(_detect_risk_reducers(page_text))
    signals.append(_detect_legitimacy_signals(page_text))
    
    # FRICTION (3 signals)
    signals.append(_detect_pricing_visibility(page_text))
    signals.append(_detect_form_friction(page_text, ctas))
    signals.append(await _detect_cognitive_load(page_text, headlines))
    
    # Ensure we always return exactly 12 signals in the correct order
    signal_dict = {s["id"]: s for s in signals}
    ordered_signals = []
    for def_signal in SIGNAL_DEFINITIONS:
        if def_signal["id"] in signal_dict:
            ordered_signals.append(signal_dict[def_signal["id"]])
        else:
            # Fallback: create unclear signal
            ordered_signals.append({
                "id": def_signal["id"],
                "label": def_signal["label"],
                "category": def_signal["category"],
                "status": "unclear",
                "confidence": 0.3,
                "reason": "Insufficient visible evidence in the provided content.",
                "recommendation": f"Add more content to analyze {def_signal['label']}"
            })
    
    # Calculate summary
    summary = _calculate_summary(ordered_signals)
    
    return {
        "signals": ordered_signals,
        "summary": summary
    }
