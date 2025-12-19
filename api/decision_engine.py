"""
Decision Engine v1 - Product Critical Module

This engine diagnoses ONE decision failure and outputs ONE concrete fix.
No dashboards, no extra analytics, no multiple insights.

Location: api/decision_engine.py
System Prompt: Defined in DECISION_ENGINE_V1_SYSTEM_PROMPT constant
API Endpoint: POST /api/brain/decision-engine (via router)
"""

import json
import logging
import os
import re
from collections import defaultdict, deque, Counter
from typing import Literal, Optional, Deque, Dict, List, Any
from pydantic import BaseModel, Field, ValidationError, validator
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urlparse
from openai import OpenAI
from fastapi import APIRouter, HTTPException, Query
import httpx
from bs4 import BeautifulSoup
import asyncio

router = APIRouter()
logger = logging.getLogger("decision_engine")

# Import decision memory layer
try:
    from utils.decision_memory_layer import (
        decision_memory_layer,
        DecisionHistoryInsight,
        FatigueLevel
    )
except ImportError:
    # Fallback if memory layer not available
    decision_memory_layer = None
    DecisionHistoryInsight = None
    FatigueLevel = None
    logger.warning("Decision memory layer not available. Memory features disabled.")

# Import decision stage inference
try:
    from utils.decision_stage_inference import (
        decision_stage_inference,
        DecisionStage,
        FrictionSeverity
    )
except ImportError:
    # Fallback if stage inference not available
    decision_stage_inference = None
    DecisionStage = None
    FrictionSeverity = None
    logger.warning("Decision stage inference not available. Stage features disabled.")

# Import high-trust platform config
try:
    from config.high_trust_platforms import is_high_trust_platform
except ImportError:
    # Fallback if config module doesn't exist
    def is_high_trust_platform(url: str) -> bool:
        return False

# Load environment variables
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
else:
    load_dotenv()

# ====================================================
# PLATFORM DETECTION
# ====================================================

def detect_platform_from_url(url: str) -> str:
    """
    Very simple platform detector based on hostname.
    Returns values like: "amazon_product_page", "generic".
    """
    if not url:
        return "generic"
    
    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        hostname = ""
    
    hostname = hostname.lower()
    
    if "amazon." in hostname:
        return "amazon_product_page"
    # TODO: in future add ebay, etsy, etc.
    return "generic"


def default_cta_subtext(platform: str) -> str:
    """
    Get default CTA subtext based on platform.
    For Amazon, return empty string as seller cannot modify CTA.
    """
    if platform == "amazon_product_page":
        return ""
    return "Know exactly why users don't decide, and what to change first."


# ====================================================
# DECISION MEMORY STORE
# ====================================================

class DecisionMemoryItem(BaseModel):
    """Single memory item for a decision analysis"""
    url: str
    blocker: str
    location: str


class DecisionMemoryStore:
    """In-memory store for decision analysis history"""
    
    def __init__(self, max_items_per_url: int = 10):
        self._store: Dict[str, Deque[DecisionMemoryItem]] = defaultdict(
            lambda: deque(maxlen=max_items_per_url)
        )
    
    def add(self, item: DecisionMemoryItem) -> None:
        """Add a new memory item for a URL"""
        self._store[item.url].append(item)
    
    def get(self, url: str) -> List[DecisionMemoryItem]:
        """Get all memory items for a URL"""
        return list(self._store.get(url, []))


# Global memory store instance
decision_memory = DecisionMemoryStore()


def summarize_chronic_patterns(items: List[DecisionMemoryItem]) -> Dict[str, Any]:
    """
    Summarize chronic decision blockers based on history items.
    
    Returns a dict like:
    {
        "Outcome Unclear": {
            "count": 4,
            "top_locations": ["Pricing", "Hero"],
            "severity": "high",
        },
        ...
    }
    """
    if not items:
        return {}
    
    blocker_counts = Counter()
    blocker_locations: Dict[str, Counter] = {}
    
    for it in items:
        blocker = it.blocker
        blocker_counts[blocker] += 1
        blocker_locations.setdefault(blocker, Counter())
        # برای هر blocker، location متناظر را هم بشمار
        blocker_locations[blocker][it.location] += 1
    
    chronic: Dict[str, Any] = {}
    for blocker, count in blocker_counts.items():
        # اگر کمتر از 3 بار دیده شده، فعلاً chronic حساب نکن
        if count < 3:
            continue
        
        loc_counter = blocker_locations.get(blocker, Counter())
        top_locations = [loc for loc, _ in loc_counter.most_common(3)]
        
        # severity ساده بر اساس تعداد تکرار
        if count >= 7:
            severity = "high"
        elif count >= 4:
            severity = "medium"
        else:
            severity = "low"
        
        chronic[blocker] = {
            "count": count,
            "top_locations": top_locations,
            "severity": severity,
        }
    
    return chronic


# ====================================================
# SYSTEM PROMPT - DO NOT MODIFY WITHOUT EXPLICIT INSTRUCTION
# ====================================================

DECISION_ENGINE_V1_SYSTEM_PROMPT = """# THIS IS THE SYSTEM PROMPT FOR Decision Engine v1
# DO NOT MODIFY LOGIC, TONE, OR RULES WITHOUT EXPLICIT INSTRUCTION

You are a Decision Failure Diagnosis Engine.

Your ONLY job:
Detect why a user hesitates at the moment of decision
and tell them the FIRST thing they must change.

This is NOT a marketing analysis tool.
This is NOT a behavioral explanation engine.
This is NOT allowed to provide multiple insights.

CORE RULES (NON-NEGOTIABLE):

1. You MUST identify exactly ONE primary decision blocker.
   - If you see multiple issues, choose ONLY the one that causes the highest hesitation.
   - Do NOT list or mention secondary problems.

2. You MUST think in terms of DECISION FAILURE, not content quality.
   - The question you answer is:
     "Why does the user hesitate instead of deciding?"

3. You are ONLY allowed to select ONE blocker from this fixed list:
   - Outcome Unclear
   - Trust Gap
   - Risk Not Addressed
   - Effort Too High
   - Commitment Anxiety

RISK NOT ADDRESSED - SEMANTIC DEFINITION:

Risk Not Addressed applies ONLY when:
- A return, refund, cancellation, or safety policy
  is completely missing or undisclosed.

Risk Not Addressed DOES NOT apply when:
- A policy exists but is simply less visually prominent.
- The platform is known to resolve risk by default (e.g. Amazon).

Visual salience or emphasis issues are NOT considered Risk.

IMPORTANT PRIORITY RULES:

1. If hesitation is caused by fear of loss, refund uncertainty, cancellation policy, money risk, or irreversible commitment,
   you MUST select "Risk Not Addressed" ONLY if the policy is completely missing or undisclosed.
   If any policy exists (even if less prominent), do NOT choose "Risk Not Addressed".

2. Outcome Unclear is ONLY allowed when:
   - The user does NOT understand what will happen after deciding
   - OR what they will receive or experience is vague or undefined

WHEN BLOCKER = "Outcome Unclear":

The "What to change first" output MUST be generated
by selecting OR adapting ONE of the following templates ONLY.

The model is NOT allowed to invent new fix structures.

ALLOWED FIX TEMPLATES:

For generic platforms (non-Amazon):
1. "Add one line directly under the CTA: 'See the ONE reason users hesitate — and the FIRST thing to fix.'"
2. "Replace the CTA subtext with: 'Know exactly why users don't decide, and what to change first.'"
3. "Add a short promise near the CTA: 'Get a clear decision diagnosis and one immediate fix.'"

For Amazon product pages (platform == "amazon_product_page"):
- DO NOT use CTA-related templates (seller cannot modify Amazon's CTA buttons).
- Focus on seller-controllable elements:
  1. "Rewrite the product title to clearly state [specific benefit/outcome]."
  2. "Update bullet point #X to emphasize [specific value proposition]."
  3. "Add to bullet points: '[concrete benefit statement]'."
  4. "Improve the main product image to show [specific visual element]."
  5. "Enhance A+ content section to highlight [specific feature/benefit]."

FORBIDDEN:
- Any mention of reports
- Any mention of multiple areas
- Any mention of steps, audits, or summaries
- Any future or secondary deliverables

If the fix does not match ONE of the templates above,
the output is considered INVALID.

3. Lack of safety, refund clarity, cancellation terms, or downside protection
   must NEVER be classified as Outcome Unclear.

4. You MUST output a concrete, executable fix.
   - No advice.
   - No suggestions.
   - No theory.
   - Give wording or structural change that can be applied immediately.

GLOBAL FIX LANGUAGE CONSTRAINTS:

The "what_to_change_first" field MUST NEVER contain:
- References to "report", "reports", or "reporting"
- Mentions of "multiple areas", "various aspects", or "several issues"
- Words like "steps", "audit", "summary", "analysis", or "breakdown"
- Future deliverables or secondary outcomes
- Any phrasing that suggests multiple outputs or comprehensive reviews

These restrictions apply to ALL blockers, not just "Outcome Unclear".

5. You MUST be decisive, confident, and concise.
   - This output is for a business owner.
   - No academic language.
   - No hedging (avoid "might", "could", "perhaps").

6. You are NOT allowed to add explanations beyond the required structure.
   - If the output exceeds the structure, it is WRONG.

INPUT CONTEXT:

You receive:
- A landing / pricing / booking / form page
- This page represents a HIGH-STAKES DECISION
  (payment, booking, submission, commitment)

MANDATORY OUTPUT FORMAT:

Return ONLY a valid JSON object.
No markdown.
No comments.
No extra text.

{
  "decision_blocker": "",
  "why": "",
  "where": "",
  "what_to_change_first": "",
  "expected_decision_lift": ""
}

OUTPUT REQUIREMENTS:

- All fields are REQUIRED.
- "decision_blocker" MUST be exactly one value from the fixed list.
- "why" MUST contain exactly TWO sentences.
- "where" MUST be exactly one of: Hero, CTA, Pricing, Form (for generic platforms).
- For Amazon product pages (platform == "amazon_product_page"), "where" MUST be one of: Title, Bullet Points, Main Image, Gallery, A+ Content, Pricing.

LOCATION RULE:
If the selected blocker is "Risk Not Addressed",
the "where" field MUST be either "Pricing" or "Form".
It MUST NEVER be "CTA".

- "what_to_change_first" MUST be a ready-to-use text or structural change.
- "expected_decision_lift" MUST be one of:
  Low (+5–10%), Medium (+10–25%), High (+25%+)

FAILURE CONDITIONS:

Your response is INVALID if:
- More than one blocker is mentioned
- More than one fix is provided
- Marketing explanations are given
- Vague language is used
- Any text exists outside the JSON object

FINAL RULE:

If uncertain, still choose the most dominant blocker.
Indecision is not allowed.

HIGH-TRUST PLATFORM RULE:

Never repeat the same decision blocker if the page clearly belongs to a high-trust platform
and trust signals (returns, ratings, delivery) are visible.

In such cases prioritize ambiguity, differentiation, or value clarity blockers:
- Outcome Unclear (when product benefit is vague)
- Effort Too High (when decision process is complex)
- Commitment Anxiety (when commitment feels too large)

Do NOT select "Risk Not Addressed" for high-trust platforms even if risk-related hesitation seems present.
Trust and risk are already handled by the platform's established policies.

========================
PLATFORM-SPECIFIC RULES
========================

The input will include a `platform` field that indicates the type of platform.
You MUST adapt your recommendations based on this platform.

If `platform` == "amazon_product_page":

- NEVER suggest changing the main CTA button text or subtext (the seller cannot modify Amazon's global UI).
- Focus ONLY on elements the seller can control:
  - Product title
  - Bullet points
  - Product description / A+ content
  - Image gallery (what is shown in the images)
- When you mention a "Location", use locations that make sense on Amazon, e.g.:
  - "Title" (instead of "Hero")
  - "Bullet Points" (instead of "CTA")
  - "Main Image" or "Gallery" (instead of "Hero Image")
  - "A+ Content" (for product description)
  - "Pricing" (if relevant, though seller has limited control)
- Recommendations MUST be concrete and product-specific (do not use generic SaaS/analytics wording like
  "Know exactly why users don't decide").
- Make sure your suggested copy sounds appropriate for an Amazon product listing.
- The "where" field MUST be one of: "Title", "Bullet Points", "Main Image", "Gallery", "A+ Content", "Pricing"
  (NOT "Hero", "CTA", or "Form" unless they have specific Amazon meaning).

If `platform` == "generic":

- Behave as before (normal website/landing page logic).
- Use standard locations: "Hero", "CTA", "Pricing", "Form" as appropriate."""

# ====================================================
# DATA MODELS
# ====================================================

class DecisionEngineInput(BaseModel):
    """Input for Decision Engine v1"""
    content: str = Field(..., description="Landing page content (text, HTML, or URL)")
    url: Optional[str] = Field(None, description="Optional URL if content is not provided")
    channel: Optional[str] = Field("generic_saas", description="Channel type: 'generic_saas' or 'marketplace_product'. Auto-detected from URL if not provided.")


class DecisionEngineOutput(BaseModel):
    """Output for Decision Engine v1 - ONE blocker, ONE fix"""
    
    decision_blocker: Literal[
        "Outcome Unclear",
        "Trust Gap",
        "Risk Not Addressed",
        "Effort Too High",
        "Commitment Anxiety"
    ] = Field(..., description="Exactly ONE decision blocker from the fixed list")
    
    why: str = Field(..., description="Exactly TWO sentences explaining the blocker")
    
    where: Literal["Hero", "CTA", "Pricing", "Form"] = Field(
        ..., description="Where on the page the blocker occurs"
    )
    
    what_to_change_first: str = Field(
        ..., description="Ready-to-use text or structural change that can be applied immediately"
    )
    
    expected_decision_lift: Literal["Low (+5–10%)", "Medium (+10–25%)", "High (+25%+)"] = Field(
        ..., description="Expected conversion lift from implementing this fix"
    )
    
    # DEBUG MARKER: Track which code path generated this response
    response_source: Optional[str] = Field(None, description="DEBUG: Response source path marker")
    
    # Memory: Historical analysis data for this URL
    memory: Optional[Dict[str, Any]] = Field(None, description="Historical analysis data for this URL")
    
    # Chronic patterns: Recurring blockers that appear frequently
    chronic_patterns: Optional[Dict[str, Any]] = Field(None, description="Chronic decision blocker patterns based on history")
    
    # Decision History Insight: Analysis of decision history when memory exists
    decision_history_insight: Optional[Dict[str, Any]] = Field(None, description="Decision history insight when memory exists")
    
    # Decision Stage Assessment: Inferred decision stage and friction severity
    decision_stage_assessment: Optional[Dict[str, Any]] = Field(None, description="Decision stage assessment and friction severity adjustment")
    
    # Context: Additional context data extracted from the page
    context: Optional[Dict[str, Any]] = Field(None, description="Context data including business_type, price_level, decision_depth, user_intent_stage, platform, url")
    
    # Confidence: Confidence score for the primary outcome (0-100)
    confidence: Optional[float] = Field(None, ge=0, le=100, description="Confidence score for the primary decision blocker analysis (0-100)")
    
    @validator('why')
    @classmethod
    def validate_why_two_sentences(cls, v: str) -> str:
        """Validate that 'why' contains exactly two sentences"""
        sentences = [s.strip() for s in v.replace('!', '.').replace('?', '.').split('.') if s.strip()]
        if len(sentences) != 2:
            raise ValueError(f"'why' must contain exactly TWO sentences. Found {len(sentences)} sentences.")
        return v


# ====================================================
# VALIDATION HELPERS
# ====================================================

VALID_DECISION_BLOCKERS = {
    "Outcome Unclear",
    "Trust Gap",
    "Risk Not Addressed",
    "Effort Too High",
    "Commitment Anxiety"
}

VALID_WHERE = {"Hero", "CTA", "Pricing", "Form"}

VALID_DECISION_LIFT = {
    "Low (+5–10%)",
    "Medium (+10–25%)",
    "High (+25%+)"
}


def validate_decision_blocker(
    blocker: str, 
    trust_signals: dict, 
    is_high_trust_platform: bool
) -> bool:
    """
    BUSINESS LOGIC validation: Hard validation layer AFTER model output.
    
    This is NOT AI logic - this is BUSINESS LOGIC that enforces business rules.
    
    Args:
        blocker: The decision blocker selected by the model
        trust_signals: Dict with keys: has_free_returns, has_delivery_date, has_ratings, has_trust_badges
        is_high_trust_platform: Whether the platform is in high-trust list
    
    Returns:
        True if blocker is valid, False if it should be rejected
    """
    if not is_high_trust_platform:
        return True  # No restriction for non-high-trust platforms
    
    if blocker == "Risk Not Addressed":
        # Count trust signals
        trust_signal_count = sum([
            trust_signals.get('has_free_returns', False),
            trust_signals.get('has_delivery_date', False),
            trust_signals.get('has_ratings', False),
            trust_signals.get('has_trust_badges', False)
        ])
        
        # BUSINESS LOGIC: If high-trust platform AND 2+ trust signals, reject Risk Not Addressed
        if trust_signal_count >= 2:
            logger.info(
                f"Risk Not Addressed suppressed due to high-trust platform. "
                f"Trust signals detected: {trust_signal_count}"
            )
            return False
    
    return True


def get_allowed_blockers_for_retry(is_high_trust_platform: bool) -> list:
    """
    Get allowed blockers list for retry when Risk Not Addressed is suppressed.
    
    Args:
        is_high_trust_platform: Whether the platform is high-trust
    
    Returns:
        List of allowed blockers
    """
    if is_high_trust_platform:
        # For high-trust platforms, exclude Risk Not Addressed
        return ["Outcome Unclear", "Trust Gap", "Effort Too High", "Commitment Anxiety"]
    else:
        # For regular platforms, all blockers are allowed
        return list(VALID_DECISION_BLOCKERS)


# ====================================================
# FIX TEMPLATES BY CHANNEL
# ====================================================

FIX_TEMPLATES = {
    "Outcome Unclear": {
        "generic_saas": {
            "Hero": [
                "Add one line directly under the CTA: 'See the ONE reason users hesitate — and the FIRST thing to fix.'"
            ],
            "CTA": [
                "Replace the CTA subtext with: 'Know exactly why users don't decide, and what to change first.'"
            ],
            "Pricing": [
                "Add one line under the CTA: 'See the ONE reason users hesitate — and the FIRST thing to fix.'"
            ],
            "Form": [
                "Add a short promise near the CTA: 'Get a clear decision diagnosis and one immediate fix.'"
            ]
        },
        "marketplace_product": {
            "Hero": [
                "Add one clear benefit line above the price, e.g.: 'Slim MagSafe protection without hiding your iPhone design.'",
                "Emphasize the main outcome: 'Keeps your iPhone safe from drops while staying thin and lightweight.'"
            ],
            "CTA": [
                "Add a benefit-focused line above the Add to Cart button, e.g.: 'Premium protection that doesn't bulk up your phone.'"
            ],
            "Pricing": [
                "Add one clear benefit line above the price, e.g.: 'Slim MagSafe protection without hiding your iPhone design.'",
                "Emphasize what makes this product different: 'Keeps your iPhone safe from drops while staying thin and lightweight.'"
            ],
            "Form": [
                "Add a product-specific benefit near the purchase button, e.g.: 'Premium quality that protects without adding bulk.'"
            ]
        }
    },
    "Effort Too High": {
        "generic_saas": {
            "Hero": [
                "Simplify the value proposition: reduce to one clear benefit sentence."
            ],
            "CTA": [
                "Make the CTA action clearer: specify what happens after clicking."
            ],
            "Pricing": [
                "Simplify pricing explanation: show one clear price point."
            ],
            "Form": [
                "Reduce form fields or explain why each field is needed."
            ]
        },
        "marketplace_product": {
            "Hero": [
                "Simplify product description: focus on one main benefit instead of listing features.",
                "Make the primary use case clear in one sentence."
            ],
            "CTA": [
                "Clarify what happens after clicking Add to Cart: mention delivery timeline or next steps."
            ],
            "Pricing": [
                "Show one clear price without hidden fees or complex calculations.",
                "Add simple delivery info: 'Free shipping' or 'Delivers in 2 days'."
            ],
            "Form": [
                "Streamline purchase flow: reduce steps or show progress indicator."
            ]
        }
    },
    "Commitment Anxiety": {
        "generic_saas": {
            "Hero": [
                "Add risk-reduction messaging: 'Start free, cancel anytime.'"
            ],
            "CTA": [
                "Reduce commitment: change from 'Buy now' to 'Try free for 14 days'."
            ],
            "Pricing": [
                "Add trial option or money-back guarantee near price."
            ],
            "Form": [
                "Add reassurance: 'No credit card required' or 'Cancel anytime'."
            ]
        },
        "marketplace_product": {
            "Hero": [
                "Emphasize return policy: 'Free returns within 30 days' or 'Hassle-free returns'.",
                "Add trust signal: 'Best Seller' or '10,000+ happy customers'."
            ],
            "CTA": [
                "Add return guarantee near Add to Cart: 'Free returns, no questions asked'."
            ],
            "Pricing": [
                "Add return policy near price: 'Try it risk-free with 30-day returns'.",
                "Show customer count: 'Join 50,000+ satisfied customers'."
            ],
            "Form": [
                "Emphasize easy returns or exchange policy near purchase button."
            ]
        }
    },
    "Trust Gap": {
        "generic_saas": {
            "Hero": ["Add social proof: customer count or logo wall."],
            "CTA": ["Add trust badge: 'Trusted by 1,000+ companies'."],
            "Pricing": ["Add customer testimonial or rating near price."],
            "Form": ["Add security badge or guarantee statement."]
        },
        "marketplace_product": {
            "Hero": ["Show product rating and review count prominently."],
            "CTA": ["Add seller badge or verified purchase indicator."],
            "Pricing": ["Display star rating and number of reviews near price."],
            "Form": ["Show seller reputation or verified seller badge."]
        }
    }
}


def get_fix_template(blocker: str, channel: str, where: str) -> Optional[str]:
    """
    Get fix template based on blocker, channel, and location.
    
    Args:
        blocker: Decision blocker (e.g., "Outcome Unclear")
        channel: Channel type ("generic_saas" or "marketplace_product")
        where: Location on page ("Hero", "CTA", "Pricing", "Form")
    
    Returns:
        Template string if found, None otherwise
    """
    # Try specific channel + location
    if blocker in FIX_TEMPLATES:
        if channel in FIX_TEMPLATES[blocker]:
            if where in FIX_TEMPLATES[blocker][channel]:
                templates = FIX_TEMPLATES[blocker][channel][where]
                # Return first template (or could randomize)
                return templates[0] if templates else None
    
    # Fallback to generic_saas if marketplace_product not found
    if channel == "marketplace_product" and blocker in FIX_TEMPLATES:
        if "generic_saas" in FIX_TEMPLATES[blocker]:
            if where in FIX_TEMPLATES[blocker]["generic_saas"]:
                templates = FIX_TEMPLATES[blocker]["generic_saas"][where]
                return templates[0] if templates else None
    
    return None


def validate_decision_output(data: dict, url: Optional[str] = None, should_suppress_risk_blocker: bool = False) -> dict:
    """
    Strict validation of decision engine output.
    
    Args:
        data: Raw output data from LLM
        url: Optional URL to check against high-trust platforms
        should_suppress_risk_blocker: If True, reject "Risk Not Addressed" blocker (deprecated, use url instead)
    
    Returns:
        dict: Validated data
        
    Raises:
        ValueError: If validation fails
    """
    # ====================================================
    # HARD BAN: VALIDATION-LEVEL ENFORCEMENT
    # This executes BEFORE any other validation
    # No prompt logic can override this
    # This is the SYSTEM-LEVEL guard that cannot be bypassed
    # ====================================================
    try:
        from config.high_trust_platforms import is_high_trust_platform
    except ImportError:
        # Fallback if config module doesn't exist
        def is_high_trust_platform(url: str) -> bool:
            return False
    
    # HARD BAN: Risk is never allowed on high-trust platforms
    # This check happens FIRST, before any other validation
    if url:
        blocker_raw = data.get("decision_blocker", "")
        blocker_normalized = blocker_raw.strip() if blocker_raw else ""
        
        if blocker_normalized and blocker_normalized.lower() == "risk not addressed":
            # Check if URL is a high-trust platform
            if is_high_trust_platform(url):
                raise ValueError(
                    "Risk Not Addressed is forbidden on high-trust platforms. "
                    "The platform resolves risk by default. "
                    "You MUST choose from: Outcome Unclear, Effort Too High, or Commitment Anxiety."
                )
    
    # Also check should_suppress_risk_blocker flag (backward compatibility)
    if should_suppress_risk_blocker:
        blocker = data.get("decision_blocker", "")
        if blocker == "Risk Not Addressed":
            raise ValueError(
                f"Invalid decision_blocker: '{blocker}'. "
                "HARD BAN: This page is on a high-trust marketplace platform (e.g., Amazon, Booking, Airbnb). "
                "'Risk Not Addressed' is FORBIDDEN. The platform resolves risk by default. "
                "You MUST choose from: Outcome Unclear, Effort Too High, or Commitment Anxiety."
            )
    
    # Check all required keys exist
    required_keys = {"decision_blocker", "why", "where", "what_to_change_first", "expected_decision_lift"}
    missing_keys = required_keys - set(data.keys())
    if missing_keys:
        raise ValueError(f"Missing required keys: {missing_keys}")
    
    # Check no extra keys
    extra_keys = set(data.keys()) - required_keys
    if extra_keys:
        raise ValueError(f"Extra keys not allowed: {extra_keys}")
    
    # Validate decision_blocker
    blocker = data.get("decision_blocker", "")
    
    if blocker not in VALID_DECISION_BLOCKERS:
        raise ValueError(f"Invalid decision_blocker: '{blocker}'. Must be one of {VALID_DECISION_BLOCKERS}")
    
    # Validate where
    where = data.get("where", "")
    if where not in VALID_WHERE:
        raise ValueError(f"Invalid where: '{where}'. Must be one of {VALID_WHERE}")
    
    # Validate expected_decision_lift
    lift = data.get("expected_decision_lift", "")
    if lift not in VALID_DECISION_LIFT:
        raise ValueError(f"Invalid expected_decision_lift: '{lift}'. Must be one of {VALID_DECISION_LIFT}")
    
    # Validate why has exactly two sentences
    why = data.get("why", "")
    sentences = [s.strip() for s in why.replace('!', '.').replace('?', '.').split('.') if s.strip()]
    if len(sentences) != 2:
        raise ValueError(f"'why' must contain exactly TWO sentences. Found {len(sentences)} sentences: {sentences}")
    
    # Validate what_to_change_first is not empty
    what = data.get("what_to_change_first", "").strip()
    if not what:
        raise ValueError("'what_to_change_first' cannot be empty")
    
    return data


# ====================================================
# OPENAI CLIENT
# ====================================================

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """Get or create OpenAI client"""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Try reading directly from .env file
            if env_file.exists():
                try:
                    with open(env_file, 'r', encoding='utf-8-sig') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and 'OPENAI_API_KEY' in line:
                                if '=' in line:
                                    key, value = line.split('=', 1)
                                    key = key.strip()
                                    value = value.strip()
                                    if key == 'OPENAI_API_KEY':
                                        # Remove quotes
                                        if value.startswith('"') and value.endswith('"'):
                                            value = value[1:-1]
                                        elif value.startswith("'") and value.endswith("'"):
                                            value = value[1:-1]
                                        api_key = value
                                        break
                except Exception:
                    pass
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        # Set timeout to 300 seconds (5 minutes) for long-running requests
        _client = OpenAI(api_key=api_key, timeout=300.0, max_retries=3)
    return _client


# ====================================================
# MAIN ANALYSIS FUNCTION
# ====================================================

async def analyze_decision_failure(input_data: DecisionEngineInput) -> DecisionEngineOutput:
    """
    Analyze content and return ONE decision blocker and ONE fix.
    
    This function:
    1. Extracts decision snapshot from URL if provided
    2. Checks if URL is high-trust platform and counts trust signals
    3. Modifies system prompt to suppress "Risk Not Addressed" if needed
    4. Sends content to LLM with strict system prompt
    5. Validates response strictly
    6. Returns validated output
    
    Args:
        input_data: DecisionEngineInput with content or URL
        
    Returns:
        DecisionEngineOutput with ONE blocker and ONE fix
        
    Raises:
        ValueError: If validation fails or URL extraction fails
        Exception: If API call fails
    """
    client = get_client()
    
    # Prepare user message
    user_message = input_data.content
    url_to_extract = None
    snapshot = None
    should_suppress_risk_blocker = False
    channel = input_data.channel or "generic_saas"  # Default channel
    
    # If URL is provided or content starts with http, extract snapshot
    url_to_extract = input_data.url
    if not url_to_extract and input_data.content.strip().startswith(('http://', 'https://')):
        url_to_extract = input_data.content.strip()
        user_message = ""  # Clear content since we'll use snapshot
    
    if url_to_extract:
        try:
            from utils.decision_snapshot_extractor import extract_decision_snapshot, format_snapshot_text, detect_channel
            snapshot = await extract_decision_snapshot(url_to_extract)  # AWAIT async call
            user_message = format_snapshot_text(snapshot)
            
            # Auto-detect channel from snapshot or URL
            if snapshot.get('channel'):
                channel = snapshot['channel']
            else:
                channel = detect_channel(url_to_extract)
            
            logger.info(f"Extracted decision snapshot from URL: {url_to_extract}, channel: {channel}")
            
            # Check if this is a high-trust platform - HARD BAN on Risk Not Addressed
            if is_high_trust_platform(url_to_extract):
                should_suppress_risk_blocker = True
                logger.info(
                    f"High-trust platform detected ({url_to_extract}). "
                    "HARD BAN: 'Risk Not Addressed' blocker is NOT allowed. "
                    "Must choose from: Outcome Unclear, Effort Too High, or Commitment Anxiety."
                )
        except ValueError as e:
            # Re-raise with clear error message (includes helpful guidance)
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"Failed to extract snapshot from URL: {e}", exc_info=True)
            # Provide helpful error message for common cases
            error_msg = str(e)
            if "403" in error_msg or "Forbidden" in error_msg:
                raise ValueError(
                    "This website blocks automated access (403 Forbidden). "
                    "Please manually copy the page content (headline, CTA, price, guarantee) "
                    "and paste it in the input field instead of the URL."
                )
            elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                raise ValueError(
                    "The request timed out. This usually means the website is slow or blocking requests. "
                    "Please manually copy the page content (headline, CTA, price, guarantee) "
                    "and paste it directly in the input field instead of using the URL."
                )
            raise ValueError(f"Failed to extract decision-critical content from URL: {error_msg}")
    
    # If URL provided but no snapshot extracted, detect channel from URL
    if not snapshot and (input_data.url or url_to_extract):
        try:
            from utils.decision_snapshot_extractor import detect_channel
            url_for_channel = url_to_extract or input_data.url
            if url_for_channel:
                channel = detect_channel(url_for_channel)
        except Exception:
            pass  # Keep default channel
        except ValueError as e:
            # Re-raise with clear error message (includes helpful guidance)
            raise ValueError(str(e))
        except Exception as e:
            logger.error(f"Failed to extract snapshot from URL: {e}", exc_info=True)
            # Provide helpful error message for common cases
            error_msg = str(e)
            if "403" in error_msg or "Forbidden" in error_msg:
                raise ValueError(
                    "This website blocks automated access (403 Forbidden). "
                    "Please manually copy the page content (headline, CTA, price, guarantee) "
                    "and paste it in the input field instead of the URL."
                )
            elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                raise ValueError(
                    "The request timed out. This usually means the website is slow or blocking requests. "
                    "Please manually copy the page content (headline, CTA, price, guarantee) "
                    "and paste it directly in the input field instead of using the URL."
                )
            raise ValueError(f"Failed to extract decision-critical content from URL: {error_msg}")
    
    if not user_message or not user_message.strip():
        raise ValueError("No content provided. Please provide either content text or a valid URL.")
    
    # Detect platform from URL
    page_url = url_to_extract or input_data.url
    platform = detect_platform_from_url(page_url or "")
    
    # Add platform information to user message
    if platform and platform != "generic":
        user_message = f"Platform: {platform}\n\n{user_message}"
    
    # Build system prompt - modify if risk blocker should be suppressed
    system_prompt = DECISION_ENGINE_V1_SYSTEM_PROMPT
    if should_suppress_risk_blocker:
        # HARD BAN: Remove "Risk Not Addressed" unconditionally on high-trust platforms
        system_prompt = DECISION_ENGINE_V1_SYSTEM_PROMPT.replace(
            """3. You are ONLY allowed to select ONE blocker from this fixed list:
   - Outcome Unclear
   - Trust Gap
   - Risk Not Addressed
   - Effort Too High
   - Commitment Anxiety""",
            """3. You are ONLY allowed to select ONE blocker from this fixed list:
   - Outcome Unclear
   - Trust Gap
   - Effort Too High
   - Commitment Anxiety

CRITICAL HARD BAN:
"Risk Not Addressed" is COMPLETELY FORBIDDEN for this analysis.
This page is on a high-trust marketplace platform (e.g., Amazon, Booking, Airbnb).
These platforms resolve risk by default through their established policies.

You MUST choose from:
- Outcome Unclear (if the product benefit/outcome is vague)
- Effort Too High (if the decision process is complex or confusing)
- Commitment Anxiety (if the commitment feels too large)

Do NOT attempt to reintroduce Risk through wording.
Do NOT select "Risk Not Addressed" regardless of phrasing."""
        )
        # Remove any rules specifically about "Risk Not Addressed" location
        system_prompt = system_prompt.replace(
            """LOCATION RULE:
If the selected blocker is "Risk Not Addressed",
the "where" field MUST be either "Pricing" or "Form".
It MUST NEVER be "CTA".""",
            ""
        )
        # Also remove or override the "RISK NOT ADDRESSED - SEMANTIC DEFINITION" section
        # to prevent any Risk-related reasoning
        system_prompt = system_prompt.replace(
            """RISK NOT ADDRESSED - SEMANTIC DEFINITION:

Risk Not Addressed applies ONLY when:
- A return, refund, cancellation, or safety policy
  is completely missing or undisclosed.

Risk Not Addressed DOES NOT apply when:
- A policy exists but is simply less visually prominent.
- The platform is known to resolve risk by default (e.g. Amazon).

Visual salience or emphasis issues are NOT considered Risk.""",
            """RISK NOT ADDRESSED - SEMANTIC DEFINITION:

Risk Not Addressed applies ONLY when:
- A return, refund, cancellation, or safety policy
  is completely missing or undisclosed.

Risk Not Addressed DOES NOT apply when:
- A policy exists but is simply less visually prominent.
- The platform is known to resolve risk by default (e.g. Amazon).

Visual salience or emphasis issues are NOT considered Risk.

FOR THIS ANALYSIS: "Risk Not Addressed" is HARD BANNED.
This page is on a high-trust marketplace platform.
You MUST choose Outcome Unclear, Effort Too High, or Commitment Anxiety instead."""
        )
        # Update the IMPORTANT PRIORITY RULES to remove Risk references
        system_prompt = system_prompt.replace(
            """1. If hesitation is caused by fear of loss, refund uncertainty, cancellation policy, money risk, or irreversible commitment,
   you MUST select "Risk Not Addressed" ONLY if the policy is completely missing or undisclosed.
   If any policy exists (even if less prominent), do NOT choose "Risk Not Addressed".""",
            """1. If hesitation is caused by fear of loss, refund uncertainty, cancellation policy, money risk, or irreversible commitment,
   do NOT select "Risk Not Addressed" (it is banned for this high-trust platform).
   Instead, consider if the hesitation is due to Outcome Unclear, Effort Too High, or Commitment Anxiety."""
        )
    
    
    # Retry logic for validation failures (especially Risk Not Addressed on high-trust platforms)
    max_retries = 2
    retry_count = 0
    last_validation_error = None
    
    while retry_count <= max_retries:
        # Call OpenAI API
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.2,  # Low temperature for consistent, focused output
                response_format={"type": "json_object"},  # Force JSON output
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
            )
        except Exception as exc:
            logger.exception("OpenAI API call failed: %s", exc)
            raise
        
        # Extract response
        raw_output = response.choices[0].message.content if response.choices else ""
        if not raw_output:
            raise ValueError("Empty response from model")
        
        # Parse JSON
        try:
            parsed_data = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            logger.error("Model returned non-JSON payload: %s", raw_output[:200])
            raise ValueError(f"Model response was not valid JSON: {exc}")
        
        # ====================================================
        # BUSINESS LOGIC VALIDATION LAYER (AFTER MODEL OUTPUT)
        # This is BUSINESS LOGIC, not AI logic
        # ====================================================
        blocker_from_model = parsed_data.get("decision_blocker", "")
        validation_url = url_to_extract or input_data.url
        is_high_trust = validation_url and is_high_trust_platform(validation_url) if validation_url else False
        
        # Get trust signals from snapshot if available
        trust_signals_dict = {
            'has_free_returns': snapshot.get('has_free_returns', False) if snapshot else False,
            'has_delivery_date': snapshot.get('has_delivery_date', False) if snapshot else False,
            'has_ratings': snapshot.get('has_ratings', False) if snapshot else False,
            'has_trust_badges': snapshot.get('has_trust_badges', False) if snapshot else False
        }
        
        # BUSINESS LOGIC: Validate blocker with trust signals
        blocker_is_valid = validate_decision_blocker(
            blocker_from_model,
            trust_signals_dict,
            is_high_trust
        )
        
        if not blocker_is_valid:
            # BUSINESS LOGIC: Force re-selection from remaining blockers
            logger.info("Risk Not Addressed suppressed due to high-trust platform")
            allowed_blockers = get_allowed_blockers_for_retry(is_high_trust)
            
            if retry_count < max_retries:
                retry_count += 1
                logger.warning(
                    f"Blocker validation failed: '{blocker_from_model}' rejected by business logic. "
                    f"Retrying with allowed blockers: {allowed_blockers} (attempt {retry_count}/{max_retries})..."
                )
                
                # Build forced blocker list in system prompt
                allowed_blockers_str = "\n   - ".join([f"3. You are ONLY allowed to select ONE blocker from this fixed list:"] + allowed_blockers)
                system_prompt = re.sub(
                    r'3\. You are ONLY allowed to select ONE blocker from this fixed list:.*?(?=\n\n|\nCRITICAL|\Z)',
                    f"""{allowed_blockers_str}

CRITICAL: "Risk Not Addressed" is FORBIDDEN by business logic for this high-trust platform.
You MUST choose from the list above.""",
                    system_prompt,
                    flags=re.DOTALL
                )
                continue  # Retry with updated prompt and forced blocker list
            else:
                # Max retries reached - fail with clear error
                logger.error(
                    f"Business logic validation failed after {max_retries} retries. "
                    f"Model selected '{blocker_from_model}' which is forbidden for high-trust platforms."
                )
                raise ValueError(
                    f"Business logic validation failed: '{blocker_from_model}' is not allowed "
                    f"for high-trust platforms with sufficient trust signals. "
                    f"Allowed blockers: {allowed_blockers}"
                )
        
        # Strict validation with URL-based HARD BAN
        # Use url_to_extract or fallback to input_data.url for validation
        try:
            validated_data = validate_decision_output(
                parsed_data, 
                url=validation_url,  # Pass URL for validation-level enforcement
                should_suppress_risk_blocker=should_suppress_risk_blocker
            )
        except ValueError as exc:
            last_validation_error = exc
            error_msg = str(exc)
            
            # If validation failed due to Risk Not Addressed on high-trust platform, retry
            if "Risk Not Addressed is forbidden" in error_msg or "HARD BAN" in error_msg:
                if retry_count < max_retries:
                    retry_count += 1
                    logger.warning(
                        f"Validation failed: {exc}. "
                        f"Risk Not Addressed detected on high-trust platform. "
                        f"Retrying (attempt {retry_count}/{max_retries})..."
                    )
                    # Update system prompt to be even more explicit
                    system_prompt = system_prompt.replace(
                        """CRITICAL HARD BAN:
"Risk Not Addressed" is COMPLETELY FORBIDDEN for this analysis.""",
                        """CRITICAL HARD BAN:
"Risk Not Addressed" is COMPLETELY FORBIDDEN for this analysis.
IF YOU SELECT "Risk Not Addressed", YOUR RESPONSE WILL BE REJECTED.
YOU MUST CHOOSE: Outcome Unclear, Effort Too High, or Commitment Anxiety."""
                    )
                    continue  # Retry with updated prompt
                else:
                    # Max retries reached, fail with clear error
                    logger.error(f"Validation failed after {max_retries} retries: {exc}. Response: {raw_output[:200]}")
                    raise ValueError(
                        f"Output validation failed after {max_retries} retries: {exc}. "
                        "The model persistently selected 'Risk Not Addressed' which is forbidden on high-trust platforms."
                    )
            else:
                # Other validation errors - don't retry
                logger.error("Validation failed: %s. Response: %s", exc, raw_output[:200])
                raise ValueError(f"Output validation failed: {exc}")
        
        # Validation passed - apply channel-specific template if available
        blocker = validated_data.get("decision_blocker", "")
        where = validated_data.get("where", "")
        
        # Calculate base confidence from expected_lift (needed for stage assessment fallback)
        lift = validated_data.get('expected_decision_lift', '')
        if 'High' in lift:
            base_confidence = 85.0
        elif 'Medium' in lift:
            base_confidence = 70.0
        else:
            base_confidence = 60.0
        
        # DECISION STAGE INFERENCE
        decision_stage_assessment = None
        if decision_stage_inference:
            try:
                # Extract context signals from snapshot
                cta_text = None
                has_pricing = False
                has_form = False
                has_checkout = False
                has_education = False
                has_comparison = False
                has_confirmation = False
                offer_type = None
                
                if snapshot:
                    cta_text = snapshot.get('cta')
                    has_pricing = bool(snapshot.get('price'))
                    # Infer other signals from content
                    page_text = user_message.lower() if user_message else ""
                    has_education = any(phrase in page_text for phrase in [
                        "how it works", "what is", "learn about", "understand"
                    ])
                    has_comparison = any(phrase in page_text for phrase in [
                        "compare", "vs", "versus", "features", "pricing"
                    ])
                    has_form = "form" in page_text or where == "Form"
                    has_checkout = any(phrase in page_text for phrase in [
                        "checkout", "complete purchase", "place order"
                    ])
                    has_confirmation = any(phrase in page_text for phrase in [
                        "thank you", "confirmation", "what happens next"
                    ])
                
                # Infer stage
                stage_inference = decision_stage_inference.infer_stage(
                    cta_text=cta_text,
                    page_content=user_message,
                    has_pricing=has_pricing,
                    has_form=has_form,
                    has_checkout=has_checkout,
                    has_education=has_education,
                    has_comparison=has_comparison,
                    has_confirmation=has_confirmation,
                    offer_type=offer_type
                )
                
                # Assess friction severity at this stage
                friction_assessment = decision_stage_inference.assess_friction_severity(
                    outcome=blocker,
                    stage=stage_inference.stage
                )
                
                # Build stage assessment
                # Ensure confidence is always a number (fallback to base_confidence if None)
                stage_confidence = stage_inference.confidence if stage_inference.confidence is not None else base_confidence
                decision_stage_assessment = {
                    "stage": stage_inference.stage.value,
                    "confidence": stage_confidence,
                    "signals": stage_inference.signals,
                    "explanation": stage_inference.explanation,
                    "friction_severity": friction_assessment.severity.value,
                    "friction_reasoning": friction_assessment.reasoning,
                    "friction_recommendation": friction_assessment.recommendation
                }
                
                logger.info(
                    f"Inferred decision stage: {stage_inference.stage.value} "
                    f"({stage_inference.confidence:.0f}% confidence). "
                    f"Friction severity: {friction_assessment.severity.value}"
                )
                
                # Adjust recommendation if friction is natural/acceptable
                if friction_assessment.severity in [FrictionSeverity.NATURAL, FrictionSeverity.ACCEPTABLE]:
                    # Don't change the fix, but note that it may not need fixing
                    logger.info(
                        f"Friction '{blocker}' is {friction_assessment.severity.value} at "
                        f"{stage_inference.stage.value} stage. Consider guidance over fixing."
                    )
                
            except Exception as stage_error:
                logger.warning(f"Failed to infer decision stage: {stage_error}", exc_info=True)
        
        # For Amazon, skip CTA-related templates and use platform-specific logic
        if platform == "amazon_product_page":
            # Don't apply generic CTA templates for Amazon
            template = None
        else:
            # Try to get channel-specific template
            template = get_fix_template(blocker, channel, where)
        if template:
            validated_data["what_to_change_first"] = template
            logger.info(
                f"Applied channel-specific template: blocker={blocker}, "
                f"channel={channel}, where={where}"
            )
        
        # Create output model
        try:
            # Add debug marker for primary success path
            validated_data["response_source"] = "decision_engine_primary"
            output = DecisionEngineOutput(**validated_data)
            logger.info(
                f"✅ Decision Engine success path: response_source=decision_engine_primary, "
                f"blocker={validated_data.get('decision_blocker')}, channel={channel}"
            )
            
            # Determine the URL to use for memory (prefer extracted URL, fallback to input URL)
            page_url = url_to_extract or input_data.url
            context_id = page_url or "default_context"  # Use URL as context ID
            
            # base_confidence already calculated above
            
            # MEMORY-AWARE ANALYSIS (before saving new analysis)
            decision_history_insight = None
            adjusted_confidence = base_confidence
            confidence_reason = ""
            current_stage = None
            
            # Extract current stage from stage assessment if available
            if decision_stage_assessment:
                current_stage = decision_stage_assessment.get('stage')
            
            if decision_memory_layer and context_id:
                try:
                    # Check if we should suppress repeated fixes
                    proposed_fix = validated_data.get('what_to_change_first', '')
                    should_suppress, suppress_reason = decision_memory_layer.suppress_repeated_fixes(
                        context_id, proposed_fix
                    )
                    
                    if should_suppress and suppress_reason:
                        logger.warning(f"Repeated fix detected: {suppress_reason}")
                        # Note: We don't change the fix here, but we note it in history insight
                    
                    # Adjust confidence based on memory (stage-aware)
                    blocker = validated_data.get('decision_blocker', '')
                    if current_stage:
                        # Use stage-aware confidence adjustment
                        adjusted_confidence, confidence_reason = decision_memory_layer.adjust_confidence_with_memory_stage_aware(
                            context_id, blocker, base_confidence, current_stage
                        )
                    else:
                        # Fallback to regular confidence adjustment
                        adjusted_confidence, confidence_reason = decision_memory_layer.adjust_confidence_with_memory(
                            context_id, blocker, base_confidence
                        )
                    
                    # Generate history insight (with stage)
                    decision_history_insight_obj = decision_memory_layer.generate_history_insight(
                        context_id, blocker, adjusted_confidence, current_stage
                    )
                    
                    # Convert to dict for JSON serialization
                    decision_history_insight = {
                        "what_failed": decision_history_insight_obj.what_failed,
                        "what_improved": decision_history_insight_obj.what_improved,
                        "what_remains_unresolved": decision_history_insight_obj.what_remains_unresolved,
                        "why_still_hesitating": decision_history_insight_obj.why_still_hesitating,
                        "trajectory_summary": decision_history_insight_obj.trajectory_summary,
                    }
                    
                    if decision_history_insight_obj.fatigue_analysis:
                        decision_history_insight["fatigue"] = {
                            "level": decision_history_insight_obj.fatigue_analysis.fatigue_level.value,
                            "indicators": decision_history_insight_obj.fatigue_analysis.indicators,
                            "recommendation": decision_history_insight_obj.fatigue_analysis.recommendation
                        }
                    
                    if decision_history_insight_obj.trust_dynamics:
                        decision_history_insight["trust_dynamics"] = {
                            "trend": decision_history_insight_obj.trust_dynamics.trust_debt_trend,
                            "consistency": decision_history_insight_obj.trust_dynamics.trust_consistency,
                            "recommendation": decision_history_insight_obj.trust_dynamics.recommendation
                        }
                    
                    # Add journey insight (Journey × Memory integration)
                    if decision_history_insight_obj.journey_insight:
                        journey = decision_history_insight_obj.journey_insight
                        decision_history_insight["journey_insight"] = {
                            "observed_stage_trajectory": journey.observed_stage_trajectory,
                            "interpretation": journey.interpretation,
                            "what_is_preventing_advancement": journey.what_is_preventing_advancement,
                            "action_recommendation": journey.action_recommendation
                        }
                        if journey.trajectory_analysis:
                            decision_history_insight["journey_insight"]["trajectory_analysis"] = {
                                "trajectory_type": journey.trajectory_analysis.trajectory_type,
                                "stage_sequence": journey.trajectory_analysis.stage_sequence,
                                "interpretation": journey.trajectory_analysis.interpretation,
                                "blocker_identified": journey.trajectory_analysis.blocker_identified,
                                "recommendation": journey.trajectory_analysis.recommendation
                            }
                    
                    logger.info(f"Generated decision history insight for context: {context_id}")
                    
                except Exception as mem_error:
                    logger.warning(f"Failed to generate history insight: {mem_error}", exc_info=True)
            
            # Save to enhanced memory layer (with stage information)
            if decision_memory_layer and context_id:
                try:
                    decision_memory_layer.add_analysis(
                        context_id=context_id,
                        primary_outcome=validated_data.get('decision_blocker', ''),
                        secondary_outcome=None,  # Could extract from 'why' if needed
                        confidence_score=adjusted_confidence,
                        location=validated_data.get('where', ''),
                        what_to_change=validated_data.get('what_to_change_first', ''),
                        expected_lift=validated_data.get('expected_decision_lift', ''),
                        url=page_url or "",
                        inferred_stage=current_stage  # Store inferred decision stage
                    )
                    logger.debug(f"Saved analysis to enhanced memory layer for context: {context_id}, stage: {current_stage}")
                except Exception as mem_error:
                    logger.warning(f"Failed to save to enhanced memory: {mem_error}", exc_info=True)
            
            # Also save to legacy memory store for backward compatibility
            if page_url:
                try:
                    memory_item = DecisionMemoryItem(
                        url=page_url,
                        blocker=validated_data.get('decision_blocker', ''),
                        location=validated_data.get('where', '')
                    )
                    decision_memory.add(memory_item)
                    logger.debug(f"Saved decision analysis to legacy memory for URL: {page_url}")
                except Exception as mem_error:
                    logger.warning(f"Failed to save to legacy memory: {mem_error}", exc_info=True)
            
            # Calculate and attach legacy memory summary and chronic patterns
            if page_url:
                try:
                    history_items = decision_memory.get(page_url)
                    if history_items:
                        # Count most common blockers and locations
                        blocker_counter = Counter(item.blocker for item in history_items)
                        location_counter = Counter(item.location for item in history_items)
                        
                        memory_summary = {
                            "times_seen": len(history_items),
                            "most_common_blockers": [
                                {"blocker": blocker, "count": count}
                                for blocker, count in blocker_counter.most_common(3)
                            ],
                            "most_common_locations": [
                                {"location": location, "count": count}
                                for location, count in location_counter.most_common(3)
                            ],
                            "last_blockers": [
                                {"blocker": item.blocker, "location": item.location}
                                for item in history_items[-5:]  # Last 5 analyses
                            ]
                        }
                        
                        # Calculate chronic patterns
                        chronic = summarize_chronic_patterns(history_items)
                        
                        # Update output with memory data and chronic patterns
                        output.memory = memory_summary
                        output.chronic_patterns = chronic if chronic else None
                        logger.debug(
                            f"Attached legacy memory summary: {len(history_items)} items, "
                            f"chronic patterns: {len(chronic)} patterns for URL: {page_url}"
                        )
                except Exception as mem_error:
                    logger.warning(f"Failed to calculate legacy memory summary: {mem_error}", exc_info=True)
            
            # Attach decision history insight
            if decision_history_insight:
                output.decision_history_insight = decision_history_insight
                logger.debug(f"Attached decision history insight to output")
            
            # Attach decision stage assessment
            if decision_stage_assessment:
                output.decision_stage_assessment = decision_stage_assessment
                logger.debug(f"Attached decision stage assessment to output")
            
            # Always set confidence (use adjusted_confidence if available, otherwise base_confidence)
            output.confidence = adjusted_confidence
            logger.debug(f"Set confidence to {adjusted_confidence}%")
            
            return output
        except ValidationError as exc:
            logger.error("Pydantic validation failed: %s", exc)
            raise ValueError(f"Output model validation failed: {exc}")
    
    # This should never be reached, but handle edge case
    if last_validation_error:
        raise ValueError(f"Failed after {max_retries} retries: {last_validation_error}")
    raise ValueError("Unexpected error in retry loop")


# ====================================================
# ROUTER ENDPOINT
# ====================================================

@router.post("/decision-engine")
async def decision_engine_endpoint(input_data: DecisionEngineInput):
    """
    Decision Engine v1 - Product Critical Module
    
    Diagnoses ONE decision failure and outputs ONE concrete fix.
    No dashboards, no extra analytics, no multiple insights.
    
    This endpoint:
    - Identifies exactly ONE primary decision blocker
    - Returns exactly ONE actionable fix
    - Validates output strictly (rejects invalid responses)
    """
    try:
        result = await analyze_decision_failure(input_data)  # AWAIT async call
        
        # Extract context data from snapshot if available
        context_data = {}
        url_to_extract = input_data.url
        if not url_to_extract and input_data.content.strip().startswith(('http://', 'https://')):
            url_to_extract = input_data.content.strip()
        
        if url_to_extract:
            context_data["url"] = url_to_extract
            platform = detect_platform_from_url(url_to_extract)
            if platform:
                context_data["platform"] = platform
            
            try:
                from utils.decision_snapshot_extractor import extract_decision_snapshot
                snapshot = await extract_decision_snapshot(url_to_extract)  # AWAIT async call
                
                # Extract additional context from snapshot if available
                if snapshot:
                    # Infer business type from channel
                    if snapshot.get('channel'):
                        channel = snapshot.get('channel')
                        if channel == "marketplace_product":
                            context_data["business_type"] = "marketplace"
                        elif channel == "generic_saas":
                            context_data["business_type"] = "saas"
                    
                    # Infer price level
                    if snapshot.get('price'):
                        context_data["price_level"] = "visible"
                    else:
                        context_data["price_level"] = "not_visible"
                    
                    # Infer decision depth from available elements
                    elements_count = sum([
                        1 if snapshot.get('hero_headline') else 0,
                        1 if snapshot.get('cta') else 0,
                        1 if snapshot.get('price') else 0,
                        1 if snapshot.get('guarantee_risk') else 0
                    ])
                    if elements_count >= 3:
                        context_data["decision_depth"] = "high_stakes"
                    elif elements_count >= 2:
                        context_data["decision_depth"] = "moderate"
                    else:
                        context_data["decision_depth"] = "low"
                    
                    # User intent stage (simplified inference)
                    if snapshot.get('has_free_returns') or snapshot.get('has_delivery_date'):
                        context_data["user_intent_stage"] = "evaluation"
                    elif snapshot.get('cta'):
                        context_data["user_intent_stage"] = "decision"
                    else:
                        context_data["user_intent_stage"] = "awareness"
            except Exception as e:
                logger.warning(f"Could not extract context data from snapshot: {e}")
        
        # Add context to result
        result_dict = result.dict()
        result_dict["context"] = context_data if context_data else None
        
        # Create new DecisionEngineOutput with context
        result_with_context = DecisionEngineOutput(**result_dict)
        
        # Convert to dict and add analysisStatus for frontend compatibility
        response_dict = result_with_context.dict()
        response_dict["analysisStatus"] = "ok"  # Add analysisStatus field for Next.js frontend
        
        # DEBUG: Log the source marker if present
        if hasattr(result, 'response_source'):
            logger.info(f"🔍 DEBUG: Returning result with response_source={result.response_source}, blocker={result.decision_blocker}")
        else:
            logger.warning("🔍 DEBUG: Result has no response_source marker! This should not happen.")
        return response_dict
    except ValueError as e:
        # Validation errors are client errors
        error_msg = str(e)
        logger.error(f"🔍 DEBUG: Exception path (ValueError) - Decision engine validation error: {e}")
        # Preserve helpful error messages (especially 403 errors)
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        # Other exceptions
        error_msg = str(e)
        logger.error(f"🔍 DEBUG: Exception path (Exception) - Decision engine error: {type(e).__name__}: {e}", exc_info=True)
        # Check if this is a 403 or similar helpful error that should be preserved
        if "403" in error_msg or "forbidden" in error_msg.lower() or "blocks automated access" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        raise HTTPException(status_code=500, detail=f"Decision engine failed: {error_msg}")

@router.post("/decision-engine/report")
async def decision_engine_report_endpoint(
    input_data: DecisionEngineInput,
    format: Optional[str] = Query("markdown", description="Output format: 'markdown' or 'json'")
):
    """
    Decision Engine v1 - Client-Ready Report Format
    
    Returns a formatted, client-ready decision report with 7 structured sections:
    1. Executive Decision Summary
    2. Context Snapshot
    3. Decision Failure Breakdown
    4. What To Fix First
    5. Actionable Recommendations
    6. What This Will Improve
    7. Next Diagnostic Step
    
    This endpoint provides the same analysis as /decision-engine but formats it
    as a professional diagnostic report suitable for direct client delivery.
    """
    try:
        from utils.client_report_formatter import format_decision_report
        
        # Get decision analysis
        result = await analyze_decision_failure(input_data)  # AWAIT async call
        
        # Convert Pydantic model to dict
        decision_output = result.dict()
        
        # Extract context data from snapshot if available
        context_data = {}
        url_to_extract = input_data.url
        if not url_to_extract and input_data.content.strip().startswith(('http://', 'https://')):
            url_to_extract = input_data.content.strip()
        
        if url_to_extract:
            context_data["url"] = url_to_extract
            platform = detect_platform_from_url(url_to_extract)
            if platform:
                context_data["platform"] = platform
            
            try:
                from utils.decision_snapshot_extractor import extract_decision_snapshot
                snapshot = await extract_decision_snapshot(url_to_extract)  # AWAIT async call
                
                # Extract additional context from snapshot if available
                if snapshot:
                    # Infer business type from channel
                    if snapshot.get('channel'):
                        channel = snapshot.get('channel')
                        if channel == "marketplace_product":
                            context_data["business_type"] = "marketplace"
                        elif channel == "generic_saas":
                            context_data["business_type"] = "saas"
                    
                    # Infer price level
                    if snapshot.get('price'):
                        context_data["price_level"] = "visible"
                    else:
                        context_data["price_level"] = "not_visible"
                    
                    # Infer decision depth from available elements
                    elements_count = sum([
                        1 if snapshot.get('hero_headline') else 0,
                        1 if snapshot.get('cta') else 0,
                        1 if snapshot.get('price') else 0,
                        1 if snapshot.get('guarantee_risk') else 0
                    ])
                    if elements_count >= 3:
                        context_data["decision_depth"] = "high_stakes"
                    elif elements_count >= 2:
                        context_data["decision_depth"] = "moderate"
                    else:
                        context_data["decision_depth"] = "low"
                    
                    # User intent stage (simplified inference)
                    if snapshot.get('has_free_returns') or snapshot.get('has_delivery_date'):
                        context_data["user_intent_stage"] = "evaluation"
                    elif snapshot.get('cta'):
                        context_data["user_intent_stage"] = "decision"
                    else:
                        context_data["user_intent_stage"] = "awareness"
            except Exception as e:
                logger.warning(f"Could not extract context data from snapshot: {e}")
        
        # Format the report
        if format == "json":
            # Return structured JSON format
            report_text = format_decision_report(decision_output, context_data)
            return {
                "report": report_text,
                "raw_analysis": decision_output,
                "context": context_data
            }
        else:
            # Return markdown format
            report_text = format_decision_report(decision_output, context_data)
            return {
                "report": report_text,
                "format": "markdown"
            }
    except ValueError as e:
        error_msg = str(e)
        logger.error(f"Decision engine report error (ValueError): {e}")
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Decision engine report error: {type(e).__name__}: {e}", exc_info=True)
        if "403" in error_msg or "forbidden" in error_msg.lower() or "blocks automated access" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        raise HTTPException(status_code=500, detail=f"Decision report generation failed: {error_msg}")


class ReportFromUrlInput(BaseModel):
    """Input for report-from-url endpoint"""
    url: str = Field(..., description="URL to analyze")
    refresh: Optional[bool] = Field(False, description="Force refresh, bypass cache")
    timeoutSec: Optional[int] = Field(45, description="HTTP request timeout in seconds")


def _extract_content_from_html(html: str, max_chars: int = 6000) -> str:
    """
    Extract meaningful content from HTML:
    - Title and meta description
    - h1/h2/h3 headings
    - Body visible text (strip script/style/nav/footer)
    """
    # BeautifulSoup will handle encoding from the already-decoded string
    soup = BeautifulSoup(html, "lxml", from_encoding="utf-8")
    
    # Remove script, style, nav, footer
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    
    parts = []
    
    # Title
    title_tag = soup.find("title")
    if title_tag:
        parts.append(f"Title: {title_tag.get_text(strip=True)}")
    
    # Meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        parts.append(f"Meta Description: {meta_desc.get('content')}")
    
    # Headings
    for heading in soup.find_all(["h1", "h2", "h3"]):
        text = heading.get_text(strip=True)
        if text:
            parts.append(text)
    
    # Body text
    body = soup.find("body")
    if body:
        body_text = body.get_text(separator="\n", strip=True)
        # Clean up excessive whitespace
        lines = [line.strip() for line in body_text.splitlines() if line.strip()]
        body_clean = "\n".join(lines)
        parts.append(body_clean)
    
    # Combine and limit
    combined = "\n\n".join(parts)
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "..."
    
    return combined


@router.post("/decision-engine/report-from-url")
async def decision_engine_report_from_url(payload: ReportFromUrlInput):
    """
    Generate decision engine report from URL.
    
    Automatically:
    1. Fetches HTML from URL
    2. Extracts content (title, meta, headings, body text)
    3. Captures screenshot
    4. Runs visual trust analysis
    5. Generates decision report
    
    Returns report with analysisStatus, url, contentPreview, visualTrust, and decisionReport.
    """
    url = payload.url.strip()
    timeout_sec = payload.timeoutSec or 45
    
    # Validate URL
    if not url or not isinstance(url, str):
        return {
            "analysisStatus": "error",
            "step": "validation",
            "errorMessage": "url must be a non-empty string"
        }
    
    if not url.startswith(("http://", "https://")):
        return {
            "analysisStatus": "error",
            "step": "validation",
            "errorMessage": "url must start with http:// or https://"
        }
    
    # Step 1: Fetch HTML
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_sec) as client:
            response = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            )
            response.raise_for_status()
            
            # Properly decode HTML content - ROOT FIX
            # Get bytes first, then detect and decode encoding correctly
            html_bytes = response.content
            
            # Detect encoding from bytes
            try:
                import chardet
                detected = chardet.detect(html_bytes)
                encoding = detected.get('encoding', 'utf-8')
                confidence = detected.get('confidence', 0)
                
                # Use detected encoding if confidence is high enough, otherwise fallback
                if confidence < 0.7:
                    # Try to get encoding from response headers first
                    if response.encoding and response.encoding.lower() != 'iso-8859-1':  # iso-8859-1 is often wrong default
                        encoding = response.encoding
                    else:
                        encoding = 'utf-8'
                
                # Decode with detected/selected encoding
                html_content = html_bytes.decode(encoding, errors='replace')
            except ImportError:
                # If chardet is not available, use httpx's encoding detection
                if response.encoding:
                    html_content = html_bytes.decode(response.encoding, errors='replace')
                else:
                    # Fallback to UTF-8
                    html_content = html_bytes.decode('utf-8', errors='replace')
    except Exception as e:
        logger.exception(f"Failed to fetch URL: {e}")
        return {
            "analysisStatus": "error",
            "step": "fetch",
            "errorMessage": f"Failed to fetch URL: {str(e)[:200]}"
        }
    
    # Step 2: Extract content
    try:
        extracted_content = _extract_content_from_html(html_content, max_chars=6000)
        content_preview = extracted_content[:200] + "..." if len(extracted_content) > 200 else extracted_content
    except Exception as e:
        logger.exception(f"Failed to extract content: {e}")
        return {
            "analysisStatus": "error",
            "step": "extract",
            "errorMessage": f"Failed to extract content: {str(e)[:200]}"
        }
    
    # Step 3: Capture screenshot (using internal function, not HTTP)
    try:
        from api.routes.debug_screenshot import capture_url_png_bytes
        screenshot_bytes = await asyncio.to_thread(capture_url_png_bytes, url)
    except Exception as e:
        logger.exception(f"Failed to capture screenshot: {e}")
        return {
            "analysisStatus": "error",
            "step": "screenshot",
            "errorMessage": f"Failed to capture screenshot: {str(e)[:200]}"
        }
    
    # Step 4: Run visual trust analysis (using internal function, not HTTP)
    try:
        from .visual_trust_engine import run_visual_trust_from_bytes
        visual_trust_result = run_visual_trust_from_bytes(screenshot_bytes)
    except Exception as e:
        logger.exception(f"Failed to analyze visual trust: {e}")
        return {
            "analysisStatus": "error",
            "step": "vision",
            "errorMessage": f"Failed to analyze visual trust: {str(e)[:200]}"
        }
    
    # Step 5: Build payload and call decision engine report internally
    try:
        # Detect platform
        platform = detect_platform_from_url(url)
        channel = "marketplace_product" if platform == "amazon_product_page" else "generic_saas"
        
        # Create DecisionEngineInput
        decision_input = DecisionEngineInput(
            content=extracted_content,
            url=url,
            channel=channel
        )
        
        # Call decision engine report function internally
        decision_result = await analyze_decision_failure(decision_input)
        decision_output = decision_result.dict()
        
        # Format report (similar to report endpoint)
        try:
            from utils.client_report_formatter import format_decision_report
            context_data = {
                "url": url,
                "platform": platform,
                "source": "url-pipeline"
            }
            report_text = format_decision_report(decision_output, context_data)
        except Exception:
            # If formatter fails, use raw output
            report_text = json.dumps(decision_output, indent=2)
        
        return {
            "analysisStatus": "ok",
            "url": url,
            "contentPreview": content_preview,
            "visualTrust": visual_trust_result,
            "decisionReport": {
                "report": report_text,
                "raw_analysis": decision_output,
                "format": "markdown"
            }
        }
    except Exception as e:
        logger.exception(f"Failed to generate decision report: {e}")
        return {
            "analysisStatus": "error",
            "step": "report",
            "errorMessage": f"Failed to generate decision report: {str(e)[:200]}"
        }


