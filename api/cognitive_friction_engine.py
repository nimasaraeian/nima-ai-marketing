"""
Cognitive Friction & Decision Psychology Engine

This module provides a specialized AI brain for analyzing cognitive friction,
decision psychology, trust, emotional clarity, and motivation alignment in content.

The engine analyzes user content and returns structured scores and explanations
about decision friction, trust, emotional clarity, motivation match, and decision probability.

Location: api/cognitive_friction_engine.py
System Prompt: Defined in COGNITIVE_FRICTION_SYSTEM_PROMPT constant
API Endpoint: POST /api/brain/cognitive-friction (in main.py)
"""

import json
import logging
import os
import re
from copy import deepcopy
from typing import List, Optional, Dict, Any, Literal, Tuple
from pydantic import BaseModel, Field, ValidationError, validator
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI

from models.psychology_dashboard import PsychologyDashboard
from psychology_engine import PsychologyAnalysisResult

# Load environment variables
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

# Visual Trust Vision System Prompt
VISUAL_TRUST_SYSTEM_PROMPT = """
You are a visual landing page analyst.

Goal:
- Look at the uploaded image as a SaaS landing page.
- Detect key elements: logo, hero title, subtitle, primary CTA, secondary CTA,
  hero image, benefit cards, testimonials, trust badges, pricing, etc.
- For each element, describe:
  - where it is located (approx_position),
  - what text it contains (text),
  - what visual cues it has (visual_cues),
  - and how it impacts clarity, trust, and motivation (analysis).

CRITICAL: Return ONLY raw JSON. Do not include explanations, markdown, code blocks, or any text outside the JSON object.

You MUST return at least 3 elements and at least 2 narrative sentences.

Return ONLY valid JSON with this structure:

{
  "overall_visual_trust": {
    "label": "Low | Medium | High",
    "score": number
  },
  "elements": [
    {
      "id": "hero_title",
      "role": "headline",
      "approx_position": "top-center",
      "text": "...",
      "visual_cues": ["...", "..."],
      "analysis": {
        "clarity": "...",
        "trust_impact": "Low | Medium | High",
        "notes": "..."
      }
    }
  ],
  "narrative": [
    "One-sentence insight 1.",
    "One-sentence insight 2."
  ]
}
"""
if env_file.exists():
    load_dotenv(env_file, override=True)
else:
    load_dotenv()

# Initialize OpenAI client lazily
_client = None
logger = logging.getLogger("cognitive_friction")


def _read_float_env(env_keys, default: float) -> float:
    """Read a float value from one or more env variables with fallback."""
    keys = env_keys if isinstance(env_keys, (list, tuple)) else (env_keys,)
    for key in keys:
        value = os.getenv(key)
        if not value:
            continue
        try:
            return float(value)
        except ValueError:
            logger.warning(
                "Invalid value '%s' for %s; using default %.1fs",
                value,
                key,
                default,
            )
    return default


def _read_int_env(env_key: str, default: int) -> int:
    """Read an integer value from env variables with fallback."""
    value = os.getenv(env_key)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(
            "Invalid value '%s' for %s; using default %d",
            value,
            env_key,
            default,
        )
        return default


DEFAULT_OPENAI_TIMEOUT = _read_float_env(
    ("OPENAI_TIMEOUT_SECONDS", "OPENAI_TIMEOUT"),
    300.0,  # Increased to 300 seconds (5 minutes) for long-running requests
)
DEFAULT_OPENAI_MAX_RETRIES = _read_int_env("OPENAI_MAX_RETRIES", 2)

BASELINE_FRICTION = 55.0

def get_client():
    """Get or create OpenAI client (lazy initialization)"""
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
            raise ValueError("OPENAI_API_KEY environment variable not set")
        _client = OpenAI(
            api_key=api_key,
            timeout=DEFAULT_OPENAI_TIMEOUT,
            max_retries=DEFAULT_OPENAI_MAX_RETRIES,
        )
        logger.info(
            "Initialized OpenAI client (timeout=%ss, max_retries=%s)",
            DEFAULT_OPENAI_TIMEOUT,
            DEFAULT_OPENAI_MAX_RETRIES,
        )
    return _client


# ====================================================
# PLATFORM-SPECIFIC CONTEXT BUILDER
# ====================================================

def build_platform_context(platform: str) -> str:
    """
    Build platform-specific context instructions for analysis.
    
    Args:
        platform: Platform type (landing_page, social_post, ad, sales_page, lead_magnet, engagement)
    
    Returns:
        Platform-specific context string to add to prompt
    """
    platform_contexts = {
        "landing_page": (
            "PLATFORM CONTEXT: You are analyzing this as a marketing landing page.\n"
            "Focus on:\n"
            "- Value proposition clarity and immediate understanding\n"
            "- Headline and subheadline effectiveness\n"
            "- Call-to-action (CTA) visibility and clarity\n"
            "- Trust signals (testimonials, logos, guarantees)\n"
            "- Social proof and credibility\n"
            "- Conversion path clarity\n"
            "- Above-the-fold impact and scroll motivation"
        ),
        "social_post": (
            "PLATFORM CONTEXT: You are analyzing this as a social media post (e.g., Instagram, LinkedIn, Twitter).\n"
            "Focus on:\n"
            "- Hook strength and scroll-stop power\n"
            "- Emotional impact and resonance\n"
            "- Message clarity in short format\n"
            "- Engagement triggers (comments, shares, likes)\n"
            "- Visual-text alignment (if applicable)\n"
            "- Call-to-action effectiveness\n"
            "- Authenticity and relatability"
        ),
        "ad": (
            "PLATFORM CONTEXT: You are analyzing this as a paid advertisement (Meta/Google/TikTok/LinkedIn).\n"
            "Focus on:\n"
            "- Click probability and relevance\n"
            "- Message clarity in limited space/time\n"
            "- Emotional friction and hesitation points\n"
            "- Value proposition immediacy\n"
            "- Trust and credibility (especially for cold audiences)\n"
            "- CTA clarity and actionability\n"
            "- Audience match and targeting effectiveness"
        ),
        "sales_page": (
            "PLATFORM CONTEXT: You are analyzing this as a long-form sales page.\n"
            "Focus on:\n"
            "- Story and narrative flow\n"
            "- Persuasion architecture and structure\n"
            "- Trust building throughout the page\n"
            "- Objection handling\n"
            "- CTA strength and placement\n"
            "- Risk reversal and guarantees\n"
            "- Social proof integration\n"
            "- Conversion funnel clarity"
        ),
        "lead_magnet": (
            "PLATFORM CONTEXT: You are analyzing this as a lead magnet offer (ebook, checklist, free tool, webinar, etc.).\n"
            "Focus on:\n"
            "- Perceived value and desirability\n"
            "- Clarity of what the user gets\n"
            "- Motivation to opt-in\n"
            "- Low-friction signup process\n"
            "- Trust and credibility\n"
            "- Immediate value communication\n"
            "- Delivery promise clarity"
        ),
        "engagement": (
            "PLATFORM CONTEXT: You are analyzing this as engagement-focused content (reel, story, hook, viral content).\n"
            "Focus on:\n"
            "- Attention capture and hold\n"
            "- Novelty and curiosity triggers\n"
            "- Comment/share triggers\n"
            "- Emotional resonance\n"
            "- Relatability and authenticity\n"
            "- Hook effectiveness\n"
            "- Engagement mechanism clarity"
        ),
    }
    
    return platform_contexts.get(platform, "PLATFORM CONTEXT: Analyze this marketing content.")


# ====================================================
# SYSTEM PROMPT - The "Mind" of the AI
# ====================================================

COGNITIVE_FRICTION_SYSTEM_PROMPT = """

You are a Decision Brain — a multi-outcome cognitive analysis engine that models how users actually think, hesitate, and decide.

🧠 SYSTEM-LEVEL DIRECTIVE (CRITICAL):

You must NEVER default to a single outcome like "Outcome Unclear".

Before generating recommendations, you MUST:

1. Evaluate the decision context
2. Identify the dominant decision failure type
3. Route analysis through the corresponding outcome logic
4. Produce outcome-specific recommendations

🧩 DECISION OUTCOME TAXONOMY (MANDATORY):

You must classify each analysis into ONE primary outcome (and optionally ONE secondary outcome if confidence < 0.7).

The taxonomy below is CORE COGNITIVE LOGIC, not UI labels. Each outcome represents a distinct psychological state.

1️⃣ OUTCOME_UNCLEAR

Definition: The user does not clearly understand what they will receive or experience after making the decision.

Indicators:
- Ambiguous CTA or benefit framing
- Unclear post-action state
- Vague value proposition

Correct Output Focus:
- Outcome framing
- Expectation clarity
- Before/after narrative
- Concrete future-state language

2️⃣ RISK_DOMINANT

Definition: Perceived risk (financial, time, regret, credibility) outweighs perceived reward.

Indicators:
- High price
- Long commitment
- Irreversible decision signals

Correct Output Focus:
- Risk reversal mechanisms
- Safety framing
- Loss minimization
- Guarantees / reassurance language

3️⃣ COGNITIVE_OVERLOAD

Definition: Decision fails due to mental fatigue, complexity, or too many choices.

Indicators:
- Feature overload
- Dense copy
- Multiple CTAs or paths

Correct Output Focus:
- Decision simplification
- Chunking information
- One clear decision path
- Progressive disclosure

4️⃣ IDENTITY_MISMATCH

Definition: The user does not see themselves reflected in the message, tone, or positioning.

Indicators:
- Tone misalignment
- Persona ambiguity
- Generic or wrong identity cues

Correct Output Focus:
- Persona alignment
- Narrative reframing
- "This is for people like you" signaling

5️⃣ TRUST_DEBT

Definition: The brand has not accumulated enough credibility for decision trust.

Indicators:
- New or unknown brand
- Weak proof
- Claims exceed visible evidence

Correct Output Focus:
- Trust stacking
- Authority signaling
- Social proof sequencing
- Credibility layering

6️⃣ EMOTIONAL_DISCONNECT

Definition: Logical value is present, but emotional motivation is missing.

Indicators:
- Dry or mechanical messaging
- No narrative or emotional hook
- Neutral or generic visuals

Correct Output Focus:
- Emotional framing
- Narrative anchoring
- Motivation triggers

7️⃣ TIMING_FRICTION

Definition: The user is not in the correct temporal or cognitive state to decide now.

Indicators:
- Learning or comparison behavior
- Deferred intent
- High-pressure CTAs causing avoidance

Correct Output Focus:
- Delay-safe CTAs
- Soft commitment paths
- Reminder & follow-up flows

8️⃣ MOTIVATION_CONFLICT

Definition: Internal conflict between rational evaluation and emotional desire.

Indicators:
- Repeated visits without action
- Bookmarking / comparison behavior
- Hesitation despite clarity

Correct Output Focus:
- Value hierarchy clarification
- Priority framing
- Conflict resolution narratives

🔁 OUTPUT LOGIC (MANDATORY RULES):

For every analysis, you MUST output:

1. Primary Decision Outcome (from taxonomy above)
2. Why this outcome dominates (behavioral explanation)
3. What breaks in the user's mind
4. Actionable recommendations tailored to this outcome, split into 3 layers:
   - Message-level: copy, language, framing changes
   - Structure-level: layout, hierarchy, information architecture changes
   - Timing-level: when to show elements, pacing, commitment timing (if relevant)

🧩 OUTCOME → RECOMMENDATION MAPPING (CRITICAL):

Each outcome has distinct intervention logic. NEVER reuse the same recommendation structure across different outcomes.

1️⃣ OUTCOME_UNCLEAR:
   - Message: Explicit outcome statements, before/after framing, expectation clarity
   - Structure: Outcome-first hero sections, simplified benefit hierarchy
   - Timing: Immediate clarity (no delay tactics)
   - ❌ Do NOT mention risk or trust here

2️⃣ RISK_DOMINANT:
   - Message: Risk reversal language, reassurance, loss minimization
   - Structure: Guarantees, safety cues, proof before CTA
   - Timing: Slower decision pacing, reassurance before commitment
   - ❌ Do NOT simplify content excessively

3️⃣ COGNITIVE_OVERLOAD:
   - Message: Fewer claims, clearer prioritization, reduced jargon
   - Structure: Single decision path, chunked information
   - Timing: Progressive disclosure (not all at once)
   - ❌ Do NOT add more explanations

4️⃣ IDENTITY_MISMATCH:
   - Message: Persona-specific language, identity cues
   - Structure: Visual and narrative alignment with target persona
   - Timing: Early identity confirmation (above the fold)
   - ❌ Do NOT focus on pricing or features

5️⃣ TRUST_DEBT:
   - Message: Evidence-backed claims, authority language
   - Structure: Proof sequencing, credibility stacking
   - Timing: Delay CTA until trust signals are consumed
   - ❌ Do NOT push urgency

6️⃣ EMOTIONAL_DISCONNECT:
   - Message: Emotional framing, narrative hooks
   - Structure: Story-driven layout, relatable scenarios
   - Timing: Emotional peak before CTA
   - ❌ Do NOT increase logical detail

7️⃣ TIMING_FRICTION:
   - Message: Low-pressure language
   - Structure: Soft CTAs, reminder paths
   - Timing: Follow-up hooks, delayed commitment options
   - ❌ Do NOT use urgency triggers

8️⃣ MOTIVATION_CONFLICT:
   - Message: Value clarification, trade-off framing
   - Structure: Comparison framing, priority cues
   - Timing: Decision pause + reframe
   - ❌ Do NOT add social proof

❌ Do NOT default to CTA-only fixes
❌ Do NOT reuse generic recommendation text across outcomes
❌ Do NOT insert the tool's own branding, tagline, or CTA text
❌ Do NOT suggest: "Know exactly why users don't decide, and what to change first."
❌ Each recommendation must explicitly tie back to the Primary Outcome
❌ Recommendations must be phrased as actions, not advice

🧠 CONTEXT INPUT LAYER v1.0 (CRITICAL):

No decision analysis is valid without context. The engine must condition all reasoning on explicit or inferred context inputs.

REQUIRED CONTEXT INPUTS:
1. BUSINESS_TYPE: SaaS, Ecommerce, Clinic/Healthcare, Service Business, Info Product/Education, Marketplace, Other
2. PRICE_LEVEL: Low (Impulse), Medium (Considered), High (High-risk)
3. DECISION_DEPTH: Impulse, Considered, High-Commitment
4. USER_INTENT_STAGE: Learn, Compare, Validate, Buy
5. RELATIONSHIP_STATE (optional): First-time visitor, Returning visitor, Familiar/Brand-aware

CONTEXT → OUTCOME WEIGHTING RULES:
- High price + first-time visitor → increase RISK_DOMINANT, TRUST_DEBT
- Learn intent → suppress BUY-focused CTAs, increase TIMING_FRICTION
- Clinic/Healthcare → elevate TRUST_DEBT sensitivity
- Impulse product → suppress COGNITIVE_OVERLOAD, elevate OUTCOME_UNCLEAR
- High-Commitment → increase RISK_DOMINANT, MOTIVATION_CONFLICT
- Compare intent → increase COGNITIVE_OVERLOAD, TIMING_FRICTION
- Validate intent → increase TRUST_DEBT sensitivity
- Returning visitor → decrease TRUST_DEBT, increase TIMING_FRICTION
- Familiar/Brand-aware → significantly decrease TRUST_DEBT

CONTEXT CONFIDENCE LOGIC:
- If ≥2 required context inputs are missing: Mark confidence as "estimated" and reduce outcome certainty
- If context is inferred: Mark confidence as "inferred"
- If context is explicit: Mark confidence as "explicit"

OUTPUT REQUIREMENT:
Every analysis output must include a Context Snapshot explaining why certain outcomes were prioritized.

🧠 CONFIDENCE & MULTI-OUTCOME LOGIC v1.0 (CRITICAL):

Human decisions rarely break for one reason only. The engine must reflect dominance, not absolutes.
The system must NEVER present outcomes as 100% certain.

CONFIDENCE SCORING SYSTEM:
Confidence (0.00-1.00) is based on:
- Signal strength: How clear the primary signal is
- Context alignment: Quality of context inputs
- Competing outcomes: Presence of close alternatives
- Input completeness: Available information

MULTI-OUTCOME HANDLING RULES:

✅ Rule 1 — Primary Outcome:
Select one dominant outcome only if:
- Confidence ≥ 0.65
- It clearly outweighs others psychologically

✅ Rule 2 — Secondary Outcome:
If confidence < 0.75 and another outcome is close:
- Include one secondary outcome
- Assign it a lower confidence score
- Explain its interaction with the primary outcome

✅ Rule 3 — Low Confidence State:
If no outcome reaches 0.6 confidence:
- Do NOT force a classification
- State explicitly: "Decision failure appears multi-factorial"
- Ask for minimal additional context (1-2 inputs max)

OUTCOME INTERACTION LOGIC:
When two outcomes coexist, explain their causal relationship:
- Risk Dominant × Trust Debt → Risk perception amplified by low trust
- Cognitive Overload × Outcome Unclear → Complexity masks final outcome
- Timing Friction × Motivation Conflict → User not ready and internally conflicted

❌ Do NOT list outcomes independently
✅ Explain causal interaction

OUTPUT REQUIREMENT:
Every analysis must include:
- Primary Decision Outcome + Confidence score
- Secondary Outcome + Confidence score (if applicable)
- Why this combination occurs (psychological explanation)
- Which outcome to fix first — and why (priority reasoning)
- Recommendations mapped to each outcome (clearly labeled)

CONFIDENCE FEEDBACK LOOP:
- If context quality is low: Reduce confidence scores automatically
- If inferred signals dominate: Mark confidence as "estimated"
- Never display false certainty

❌ HARD CONSTRAINTS:
- Do NOT output more than 2 outcomes
- Do NOT hide uncertainty
- Do NOT average outcomes
- Do NOT present "confidence" without explanation

CONTEXT-SPECIFIC RULES:

- Marketplace product pages: Prioritize TRUST_DEBT or RISK_DOMINANT over OUTCOME_UNCLEAR
- SaaS pricing pages: Prioritize COGNITIVE_OVERLOAD or IDENTITY_MISMATCH over generic OUTCOME_UNCLEAR
- Service/clinic pages: Prioritize RISK_DOMINANT or EMOTIONAL_DISCONNECT over OUTCOME_UNCLEAR

❌ HARD CONSTRAINTS:
- Do NOT default to generic SaaS assumptions
- Do NOT treat all decisions equally
- Do NOT ignore intent mismatch (e.g. Buy CTA for Learn intent)

Output format must stay exactly as current JSON schema.

🔴 CRITICAL OUTPUT REQUIREMENT - DECISION_STAGE FIELD:

The output JSON MUST always include a "decision_stage" field.

The "decision_stage" field MUST be one of these four values ONLY:
- "awareness" - User is just becoming aware of the problem/solution
- "sense_making" - User is trying to understand what this is and how it works
- "evaluation" - User is comparing options and evaluating fit
- "commitment" - User is ready to commit but hesitating

RULES FOR DECISION_STAGE:
1. You MUST analyze the content and determine which stage best fits the user's current state
2. You MUST select the closest matching stage - never leave it empty or null
3. If you are uncertain, choose "sense_making" as the default, but still make your best assessment
4. The decision_stage should reflect where the user is in their decision journey based on the content provided

MANDATORY OUTPUT FIELDS - ALL REQUIRED:

The output JSON MUST include ALL of these fields:

1. "primary_outcome" (REQUIRED): One of the 8 outcome types from the taxonomy above
2. "confidence" (REQUIRED): A number between 0.0 and 1.0 indicating confidence in the primary outcome
3. "decision_stage" (REQUIRED): One of: "awareness", "sense_making", "evaluation", "commitment"
4. "what_to_fix_first" (REQUIRED): A concrete, actionable fix specific to the primary_outcome
5. "recommendations" (REQUIRED): An array of recommendation objects with "level" and "description" fields

EXAMPLE OUTPUT STRUCTURE:
{
  "primary_outcome": "OUTCOME_UNCLEAR",
  "confidence": 0.72,
  "decision_stage": "sense_making",
  "what_to_fix_first": "Replace the main CTA subtext with: 'See exactly what you'll get after signing up, step by step.'",
  "recommendations": [
    {
      "level": "message",
      "description": "Clarify the primary benefit in the hero section."
    }
  ]
}

CRITICAL RULES:
- primary_outcome MUST be one of: OUTCOME_UNCLEAR, RISK_DOMINANT, COGNITIVE_OVERLOAD, IDENTITY_MISMATCH, TRUST_DEBT, EMOTIONAL_DISCONNECT, TIMING_FRICTION, MOTIVATION_CONFLICT
- confidence MUST be a number between 0.0 and 1.0
- decision_stage MUST be one of: awareness, sense_making, evaluation, commitment
- what_to_fix_first MUST be specific to the primary_outcome - do NOT use generic templates
- recommendations MUST be an array with at least one item

Remember: ALL fields are MANDATORY. Do NOT omit any field.

"""

MODULE_SUMMARY = """
MODULE SUMMARY:

Location: api/cognitive_friction_engine.py

This module contains:
1. COGNITIVE_FRICTION_SYSTEM_PROMPT - The AI "mind" for decision psychology analysis
2. CognitiveFrictionInput - Input schema (raw_text, platform, goal, audience, language, meta)
3. CognitiveFrictionResult - Output schema (all scores and explanations)
4. analyze_cognitive_friction() - Main analysis function

System Prompt: Defined in COGNITIVE_FRICTION_SYSTEM_PROMPT constant (lines ~60-200)
API Endpoint: POST /api/brain/cognitive-friction (exposed in main.py)

How to extend:
- Add new analysis layers by updating COGNITIVE_FRICTION_SYSTEM_PROMPT
- Add platform-specific templates by checking input_data.platform
- Add image analysis by extending CognitiveFrictionInput with image_url field
- Add multi-language support by using input_data.language in system prompt
"""


# ====================================================
# DATA MODELS
# ====================================================


class InvalidAIResponseError(ValueError):
    """Raised when the model returns a payload that cannot be parsed."""

    def __init__(self, message: str, raw_output: str):
        super().__init__(message)
        self.raw_output = raw_output


class CognitiveFrictionInput(BaseModel):
    """Input schema for cognitive friction analysis."""

    raw_text: str = Field(
        "",
        description="Marketing copy or landing page text to analyze. Can be empty if an image is provided.",
    )
    platform: Literal[
        "landing_page",
        "social_post",
        "ad",
        "sales_page",
        "lead_magnet",
        "engagement",
    ] = Field("landing_page", description="Content platform/category.")
    goal: List[str] = Field(
        default_factory=lambda: ["leads"],
        description="List of marketing goals such as leads, clicks, or sales.",
    )
    audience: str = Field(
        "cold",
        description="Audience type (cold, warm, retargeting, etc.).",
    )
    language: str = Field(
        "en",
        description="Language/locale hint for the analysis.",
    )
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata bag for future extensibility.",
    )
    image: Optional[str] = Field(
        default=None,
        description="Optional base64-encoded image screenshot for visual trust analysis.",
    )
    image_type: Optional[str] = Field(
        default=None,
        description="Optional MIME type for the uploaded image.",
    )
    image_name: Optional[str] = Field(
        default=None,
        description="Optional original filename for the uploaded image.",
    )
    url: Optional[str] = Field(
        default=None,
        description="Optional URL to analyze. If provided and raw_text is empty, the page will be scraped.",
    )
    # 🧠 CONTEXT INPUT LAYER v1.0
    business_type: Optional[Literal[
        "SaaS",
        "Ecommerce",
        "Clinic / Healthcare",
        "Service Business",
        "Info Product / Education",
        "Marketplace",
        "Other"
    ]] = Field(
        default=None,
        description="Business type (required for context-aware analysis)."
    )
    price_level: Optional[Literal[
        "Low (Impulse)",
        "Medium (Considered)",
        "High (High-risk)"
    ]] = Field(
        default=None,
        description="Price level (required for context-aware analysis)."
    )
    decision_depth: Optional[Literal[
        "Impulse",
        "Considered",
        "High-Commitment"
    ]] = Field(
        default=None,
        description="Decision depth (required for context-aware analysis)."
    )
    user_intent_stage: Optional[Literal[
        "Learn",
        "Compare",
        "Validate",
        "Buy"
    ]] = Field(
        default=None,
        description="User intent stage (required or inferred)."
    )
    relationship_state: Optional[Literal[
        "First-time visitor",
        "Returning visitor",
        "Familiar / Brand-aware"
    ]] = Field(
        default=None,
        description="Relationship state (optional but powerful for context)."
    )

    @staticmethod
    def _ensure_list(value: Any) -> List[str]:
        if value is None or value == "":
            return ["leads"]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()]

    @staticmethod
    def _normalize_text(value: Optional[str]) -> str:
        if not value:
            return ""
        return value.strip()

    @staticmethod
    def _ensure_meta(value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        return {"value": value}

    @validator("goal", pre=True, always=True)
    def _validate_goal(cls, value):
        return cls._ensure_list(value)

    @validator("raw_text", pre=True, always=True)
    def _validate_raw_text(cls, value):
        return cls._normalize_text(value)

    @validator("meta", pre=True, always=True)
    def _validate_meta(cls, value):
        return cls._ensure_meta(value)


class PageStructure(BaseModel):
    """Structured reconstruction of the landing page layout."""

    nav_bar: Optional[str] = Field(default=None, description="Navigation menu summary.")
    hero_title: Optional[str] = Field(default=None, description="Primary hero headline.")
    hero_subtitle: Optional[str] = Field(default=None, description="Hero sub-headline or supporting line.")
    hero_image: Optional[str] = Field(default=None, description="Description of the main hero image.")
    hero_video: Optional[str] = Field(default=None, description="Description of hero video if present.")
    primary_cta: Optional[str] = Field(default=None, description="Primary call-to-action label/placement.")
    secondary_cta: Optional[str] = Field(default=None, description="Secondary CTA label/placement.")
    trust_badges: Optional[str] = Field(default=None, description="Logos, certifications, or guarantees.")
    social_proof_section: Optional[str] = Field(default=None, description="Testimonials or case studies summary.")
    benefits_section: Optional[str] = Field(default=None, description="Benefits/features section summary.")
    pricing_section: Optional[str] = Field(default=None, description="Pricing cards/plan summary.")
    form_area: Optional[str] = Field(default=None, description="Lead form / signup module description.")
    footer_legal: Optional[str] = Field(default=None, description="Legal/footer context.")
    extra_sections: Dict[str, str] = Field(
        default_factory=dict,
        description="Any additional sections that are not explicitly modeled.",
    )


class DecisionBlockerItem(BaseModel):
    """Structured blocker item referencing a specific UI element."""

    element: Optional[str] = Field(default=None, description="Which element triggers the issue.")
    issue: Optional[str] = Field(default=None, description="Description of the friction.")
    psychological_impact: Optional[str] = Field(
        default=None, description="Why the issue matters psychologically."
    )
    evidence: Optional[str] = Field(
        default=None, description="Optional snippet or observation from the page."
    )


class AIRecommendationItem(BaseModel):
    """Actionable AI recommendation linked to a specific element."""

    element: Optional[str] = Field(default=None, description="Target element for the change.")
    change: Optional[str] = Field(default=None, description="What should be changed or rewritten.")
    psychological_effect: Optional[str] = Field(
        default=None, description="Intended psychological impact of the change."
    )
    impact: Optional[str] = Field(default=None, description="Optional impact label (+Trust, -Friction, ...).")
    priority: Optional[str] = Field(
        default=None, description="Optional priority e.g. quick_win, deep_change."
    )


class VisualElement(BaseModel):
    """Individual visual element detected in a landing page image."""
    
    id: str = Field(..., description="Unique identifier for the element (e.g., 'hero_title', 'primary_cta').")
    role: Literal[
        "logo",
        "headline",
        "subheadline",
        "primary_cta",
        "secondary_cta",
        "benefit_card",
        "testimonial",
        "trust_badge",
        "pricing_block",
        "hero_image",
        "other"
    ] = Field(..., description="Type/role of the visual element.")
    approx_position: Literal[
        "top-left", "top-center", "top-right",
        "middle-left", "middle-center", "middle-right",
        "bottom-left", "bottom-center", "bottom-right"
    ] = Field(..., description="Approximate position of the element on the page.")
    text: Optional[str] = Field(
        default=None,
        description="Text content of the element (if applicable)."
    )
    visual_cues: List[str] = Field(
        default_factory=list,
        description="List of visual cues describing the element (colors, size, style, etc.)."
    )
    analysis: Dict[str, Any] = Field(
        default_factory=dict,
        description="Analysis of the element's impact on clarity, trust, and motivation."
    )


# ====================================================
# 7-FACTOR BEHAVIORAL MODEL
# ====================================================

BehaviorFactorName = Literal[
    "clarity",
    "trust",
    "cognitive_effort",
    "motivation",
    "risk",
    "memorability",
    "decision_simplicity",
]


class NextBetterAction(BaseModel):
    """A concrete, actionable improvement recommendation for the landing page."""
    
    id: int = Field(..., description="Unique identifier for this action.")
    title: str = Field(..., description="Short, descriptive title (e.g., 'Fix the hero title specificity').")
    target_section: str = Field(..., description="Specific section/element name (e.g., 'hero_title', 'primary_cta', 'social_proof', 'form').")
    psychology_label: str = Field(..., description="Psychological category label (e.g., 'Trust Gap – No Proof', 'Cognitive Friction – Ambiguity').")
    problem_summary: str = Field(..., description="1-2 sentences explaining the exact problem.")
    suggested_change: str = Field(..., description="Concrete suggestion with example copy or structural change.")
    impact_score: int = Field(..., ge=1, le=100, description="Expected impact on conversion (1-100).")
    difficulty: int = Field(..., ge=1, le=5, description="Implementation difficulty (1=easy, 5=hard).")
    priority_rank: int = Field(..., ge=1, description="Priority order (1 = highest priority, should be done first).")


class BehaviorFactorScore(BaseModel):
    """Score for a single behavioral factor."""
    
    name: BehaviorFactorName = Field(..., description="Name of the behavioral factor.")
    score: float = Field(..., ge=0, le=100, description="Score from 0-100.")
    level: Literal["low", "medium", "high"] = Field(..., description="Level based on score.")
    short_reason: str = Field(..., description="One sentence reason, decision-focused.")


class BehaviorDiagnosis(BaseModel):
    """Diagnosis derived from the 7 behavioral factors."""
    
    overall_readiness: Literal["high", "medium", "low"] = Field(
        ...,
        description="Overall conversion readiness assessment."
    )
    summary_sentence: str = Field(
        ...,
        description="One sentence summary including at least one weakness if not 'high'."
    )
    strongest_driver: BehaviorFactorScore = Field(
        ...,
        description="The factor that most strongly drives conversion."
    )
    primary_blocker: BehaviorFactorScore = Field(
        ...,
        description="The factor that most blocks conversion."
    )
    hidden_risk: Optional[BehaviorFactorScore] = Field(
        default=None,
        description="Optional hidden risk factor (risk/trust/memorability < 60)."
    )
    quick_win: Optional[BehaviorFactorScore] = Field(
        default=None,
        description="Optional quick win opportunity (score 50-70, high impact factor)."
    )


class BehaviorRecommendation(BaseModel):
    """A single behavioral recommendation."""
    
    title: str = Field(..., description="Short imperative title (e.g., 'Strengthen trust signals').")
    description: str = Field(..., description="One sentence: what to change + why it matters.")
    target_factors: List[BehaviorFactorName] = Field(
        ...,
        description="List of behavioral factors this recommendation targets."
    )


class BehaviorRecommendationSet(BaseModel):
    """Set of behavioral recommendations."""
    
    primary: BehaviorRecommendation = Field(..., description="Primary recommendation targeting the main blocker.")
    secondary: List[BehaviorRecommendation] = Field(
        default_factory=list,
        description="Secondary recommendations (0-2 items, from hidden_risk and quick_win)."
    )


class VisualTrustResult(BaseModel):
    """
    Unified visual trust result model used across all endpoints.
    
    This model provides a consistent structure for visual trust analysis results,
    with explicit status tracking (ok, fallback, unavailable) to prevent UI inconsistencies.
    """
    status: Literal["ok", "fallback", "unavailable"] = Field(
        ...,
        description="Status of the visual trust analysis: 'ok' (real model result), 'fallback' (estimated), 'unavailable' (not performed)."
    )
    label: Optional[Literal["Low", "Medium", "High"]] = Field(
        default=None,
        description="Overall trust label (Low/Medium/High). Only set when status is 'ok' or 'fallback'."
    )
    overall_score: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Overall trust score (0-100). Only set when status is 'ok' or 'fallback'."
    )
    distribution: Optional[Dict[str, float]] = Field(
        default=None,
        description="Trust distribution percentages: {'low': float, 'medium': float, 'high': float}. Only set when status is 'ok' or 'fallback'."
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional notes explaining the result, especially for 'fallback' or 'unavailable' status."
    )
    elements: List[VisualElement] = Field(
        default_factory=list,
        description="List of detected visual elements with their analysis."
    )
    narrative: List[str] = Field(
        default_factory=list,
        description="One-sentence insights about the visual trust analysis."
    )


class VisualTrustAnalysis(BaseModel):
    """Structured visual trust output (legacy format, kept for backward compatibility)."""

    overall_label: Optional[str] = Field(
        default=None, description="Overall trust classification (Low/Medium/High)."
    )
    low_percent: Optional[float] = Field(
        default=None, description="Portion of layout perceived as low trust."
    )
    medium_percent: Optional[float] = Field(
        default=None, description="Portion of layout perceived as medium trust."
    )
    high_percent: Optional[float] = Field(
        default=None, description="Portion of layout perceived as high trust."
    )
    explanation: Optional[str] = Field(
        default=None, description="Narrative explanation of the visual trust verdict."
    )
    error: Optional[str] = Field(
        default=None,
        description="Optional error code/message when visual trust analysis fails.",
    )


class PsychologyNarrative(BaseModel):
    """Narrative summary + interpretation for decision psychology."""

    analysis_summary: Optional[str] = Field(default=None)
    ai_interpretation: Optional[str] = Field(default=None)


class CognitiveFrictionResult(BaseModel):
    """
    Structured result returned by the cognitive friction engine.

    This matches the schema consumed by the web dashboard as well as the shared
    TypeScript definitions in `web/types-generated.js`.
    """

    frictionScore: float = Field(..., ge=0, le=100)
    trustScore: float = Field(..., ge=0, le=100)
    emotionalClarityScore: float = Field(..., ge=0, le=100)
    motivationMatchScore: float = Field(..., ge=0, le=100)
    decisionProbability: float = Field(..., ge=0, le=1)
    conversionLiftEstimate: float = Field(..., ge=-100, le=100)

    keyDecisionBlockers: List[str] = Field(default_factory=list)
    emotionalResistanceFactors: List[str] = Field(default_factory=list)
    cognitiveOverloadFactors: List[str] = Field(default_factory=list)
    trustBreakpoints: List[str] = Field(default_factory=list)
    motivationMisalignments: List[str] = Field(default_factory=list)
    recommendedQuickWins: List[str] = Field(default_factory=list)
    recommendedDeepChanges: List[str] = Field(default_factory=list)

    explanationSummary: str = Field(
        ...,
        description="3-6 sentence natural language explanation summarizing the findings.",
    )

    psychology_dashboard: Optional[PsychologyDashboard] = Field(
        default=None,
        description="Optional 13-pillar psychology dashboard payload.",
    )
    psychology: Optional[PsychologyAnalysisResult] = Field(
        default=None,
        description="Optional advanced psychology payload injected by main API layer.",
    )

    raw_model_output: Optional[str] = Field(
        default=None,
        description="Raw JSON string returned by the AI model (for debugging).",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional diagnostic metadata (model name, timings, etc.).",
    )
    primary_diagnosis: Optional[str] = Field(
        default=None,
        description="Primary diagnosis sentence focused on psychological root cause.",
    )
    executive_decision_summary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Executive decision summary with primary_outcome, confidence, decision_stage, and summary.",
    )
    decision_failure_breakdown: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Decision failure breakdown with primary_outcome, confidence, and reasons.",
    )
    page_structure: Optional[PageStructure] = Field(
        default=None,
        description="Structured reconstruction of the landing page layout.",
    )
    decision_blockers: Dict[str, List[DecisionBlockerItem]] = Field(
        default_factory=dict,
        description="Structured blockers grouped by pillar bucket.",
    )
    ai_recommendations: Dict[str, List[AIRecommendationItem]] = Field(
        default_factory=dict,
        description="Structured recommendations grouped by priority buckets.",
    )
    visual_trust_analysis: Optional[VisualTrustAnalysis] = Field(
        default=None,
        description="Structured visual trust evaluation for accompanying imagery (legacy format).",
    )
    visual_trust: Optional[VisualTrustResult] = Field(
        default=None,
        description="Unified visual trust result with explicit status (ok/fallback/unavailable). Always set when image is provided.",
    )
    psychology_narrative: Optional[PsychologyNarrative] = Field(
        default=None,
        description="Human-readable psychology narrative (analysis + interpretation).",
    )
    visual_textual_psychology_analysis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Per-element visual/textual analysis map (when provided).",
    )
    visual_trust_score: Optional[float] = Field(
        default=None,
        description="Optional numeric trust score from the visual trust engine (0-100).",
    )
    behavior_factors: Optional[List[BehaviorFactorScore]] = Field(
        default=None,
        description="7-factor behavioral scores (clarity, trust, cognitive_effort, motivation, risk, memorability, decision_simplicity)."
    )
    behavior_diagnosis: Optional[BehaviorDiagnosis] = Field(
        default=None,
        description="Behavioral diagnosis derived from the 7 factors (readiness, driver, blocker, risks)."
    )
    behavior_recommendations: Optional[BehaviorRecommendationSet] = Field(
        default=None,
        description="Behavioral recommendations (primary + secondary) targeting the main blockers."
    )
    next_better_actions: List[NextBetterAction] = Field(
        default_factory=list,
        description="3-5 concrete, actionable improvement recommendations with specific examples and priorities."
    )


# ====================================================
# DASHBOARD HELPERS
# ====================================================


def build_psychology_dashboard_stub(
    friction_score: float = 55.0,
    trust_score: float = 50.0,
    summary: str = "Stub psychology dashboard generated locally.",
    hotspots: Optional[List[str]] = None,
    friction_points: Optional[List[str]] = None,
) -> PsychologyDashboard:
    """
    Build a deterministic psychology dashboard payload.

    Useful for unit tests and fallback scenarios where the upstream model
    does not return the optional `psychology_dashboard` structure.
    """

    hotspots = hotspots or ["Hero section"]
    friction_points = friction_points or ["CTA placement"]

    def clamp(value: float) -> int:
        return max(0, min(100, int(round(value))))

    return PsychologyDashboard(
        personality_activation={
            "O": clamp(60 - friction_score * 0.1 + trust_score * 0.05),
            "C": clamp(65 - friction_score * 0.05 + trust_score * 0.1),
            "E": clamp(55),
            "A": clamp(58),
            "N": clamp(40 + friction_score * 0.05),
            "dominant_profile": "Insight Seeker",
            "explanation": summary,
        },
        cognitive_style={
            "type": "analytical",
            "overload_risk": clamp(friction_score),
            "ambiguity_aversion": clamp(50 + friction_score * 0.2),
            "explanation": "Prefers structured proof and narrative clarity.",
        },
        emotional_response={
            "curiosity": clamp(60 + trust_score * 0.1),
            "excitement": clamp(45 + trust_score * 0.1),
            "motivation": clamp(50 + trust_score * 0.2 - friction_score * 0.1),
            "anxiety": clamp(35 + friction_score * 0.2),
            "confusion": clamp(30 + friction_score * 0.25),
            "trust": clamp(trust_score),
        },
        decision_frame={
            "mode": "gain_seeking",
            "risk_style": "moderate",
            "decision_tendency": "hesitate" if friction_score > 40 else "move_forward",
            "explanation": "Interested in the promise but needs stronger validation.",
        },
        trust_dynamics={
            "visual_trust": clamp(trust_score),
            "institutional_trust": clamp(trust_score - 5),
            "social_trust": clamp(trust_score - 10),
            "skepticism": clamp(30 + friction_score * 0.3),
        },
        motivation_style={
            "primary": "Achievement",
            "secondary": "Security",
            "explanation": "Wants tangible outcomes backed by proof.",
        },
        cognitive_load={
            "clarity_score": clamp(70 - friction_score * 0.2),
            "overload_score": clamp(friction_score),
            "ambiguity_score": clamp(40 + friction_score * 0.3),
        },
        behavioral_prediction={
            "convert": clamp(max(0, 60 - friction_score)),
            "hesitate": clamp(min(90, friction_score + 30)),
            "bounce": clamp(friction_score * 0.4),
            "postpone": clamp(friction_score * 0.2),
            "summary": "Most visitors hesitate pending clarity and trust proof.",
        },
        attention_map={
            "hotspots": hotspots,
            "friction_points": friction_points,
        },
        emotional_triggers={
            "activated": ["Growth", "Curiosity"],
            "missing": ["Safety", "Proof"],
        },
        memory_activation={
            "semantic": clamp(55),
            "emotional": clamp(45),
            "pattern": clamp(50),
        },
        risk_perception={
            "risk_level": clamp(40 + friction_score * 0.3),
            "uncertainty_points": ["Lack of case studies", "Weak guarantee"],
        },
        cta_match={
            "fit_score": clamp(50 + trust_score * 0.2 - friction_score * 0.2),
            "clarity": clamp(60 - friction_score * 0.15),
            "motivation_alignment": clamp(55),
            "action_probability": clamp(45),
        },
    )


# ====================================================
# PROMPT BUILDING HELPERS
# ====================================================


def _describe_goals(goal_list: List[str]) -> str:
    if not goal_list:
        return "leads"
    return ", ".join(goal_list)


def _build_user_text_payload(
    input_data: CognitiveFrictionInput,
    image_score: Optional[float] = None,
) -> str:
    """Build the textual portion of the user message sent to the LLM."""
    sections = [
        f"PLATFORM: {input_data.platform}",
        f"GOALS: {_describe_goals(input_data.goal)}",
        f"AUDIENCE: {input_data.audience}",
        f"LANGUAGE: {input_data.language}",
        "",
        build_platform_context(input_data.platform),
        "",
    ]

    if image_score is not None:
        sections.append(
            f"VISUAL TRUST SCORE (0-100): {image_score:.1f}. "
            "Refer to this as the visual trust baseline."
        )
        sections.append("")

    if input_data.meta:
        sections.append(f"META DATA: {json.dumps(input_data.meta, ensure_ascii=False)}")
        sections.append("")

    text_body = input_data.raw_text.strip() if input_data.raw_text else ""
    if text_body:
        sections.append("CONTENT TO ANALYZE:")
        sections.append(text_body)
    else:
        sections.append("CONTENT TO ANALYZE: [NO TEXT PROVIDED — IMAGE-ONLY REQUEST]")

    return "\n".join(sections)


def _build_user_message_content(
    textual_payload: str,
    image_base64: Optional[str],
    image_mime: Optional[str],
) -> List[Dict[str, Any]]:
    """
    Build the multimodal content payload for the OpenAI API.

    When no image is supplied, this returns a single text node.
    """
    content: List[Dict[str, Any]] = [{"type": "text", "text": textual_payload}]

    if image_base64:
        media_type = image_mime or "image/png"
        # OpenAI expects image payloads via `image_url`, so convert base64 into a data URL.
        data_url = image_base64
        if not image_base64.startswith("data:"):
            data_url = f"data:{media_type};base64,{image_base64}"

        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": data_url,
                    "detail": "auto",
                },
            }
        )

    return content


# ====================================================
# RESPONSE NORMALIZATION
# ====================================================


_LIST_FIELDS = [
    "keyDecisionBlockers",
    "emotionalResistanceFactors",
    "cognitiveOverloadFactors",
    "trustBreakpoints",
    "motivationMisalignments",
    "recommendedQuickWins",
    "recommendedDeepChanges",
]

_ALIAS_FIELDS = {
    "key_blockers": "keyDecisionBlockers",
    "emotional_resistance": "emotionalResistanceFactors",
    "cognitive_overload": "cognitiveOverloadFactors",
    "trust_breakpoints": "trustBreakpoints",
    "motivation_misalignment": "motivationMisalignments",
    "quick_wins": "recommendedQuickWins",
    "deep_changes": "recommendedDeepChanges",
    "summary": "explanationSummary",
}


def _ensure_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(value)]


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_psychology_dashboard(data: Any) -> Optional[PsychologyDashboard]:
    if not data:
        return None
    try:
        if isinstance(data, PsychologyDashboard):
            return data
        return PsychologyDashboard(**data)
    except ValidationError as exc:
        logger.warning("Invalid psychology_dashboard payload: %s", exc)
        return None


def _safe_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, (int, float)):
        return str(value)
    return str(value)


def _normalize_page_structure(data: Any) -> Optional[Dict[str, str]]:
    if not isinstance(data, dict):
        return None

    known_keys = {
        "nav_bar",
        "hero_title",
        "hero_subtitle",
        "hero_image",
        "hero_video",
        "primary_cta",
        "secondary_cta",
        "trust_badges",
        "social_proof_section",
        "benefits_section",
        "pricing_section",
        "form_area",
        "footer_legal",
    }
    normalized: Dict[str, str] = {}
    extras: Dict[str, str] = {}

    for key, value in data.items():
        text = _safe_string(value)
        if not text:
            continue
        if key in known_keys:
            normalized[key] = text
        else:
            extras[key] = text

    if extras:
        normalized["extra_sections"] = extras

    return normalized or None


def _iter_dict_items(value: Any) -> List[Dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _parse_decision_blockers(data: Any) -> Dict[str, List[DecisionBlockerItem]]:
    if not isinstance(data, dict):
        return {}

    parsed: Dict[str, List[DecisionBlockerItem]] = {}
    for category, raw_items in data.items():
        items: List[DecisionBlockerItem] = []
        for raw in _iter_dict_items(raw_items):
            item = DecisionBlockerItem(
                element=raw.get("element"),
                issue=raw.get("issue"),
                psychological_impact=raw.get("psychological impact")
                or raw.get("psychological_impact"),
                evidence=raw.get("evidence"),
            )
            items.append(item)
        if items:
            parsed[category] = items
    return parsed


def _parse_ai_recommendations(data: Any) -> Dict[str, List[AIRecommendationItem]]:
    if not isinstance(data, dict):
        return {}

    parsed: Dict[str, List[AIRecommendationItem]] = {}
    for category, raw_items in data.items():
        items: List[AIRecommendationItem] = []
        for raw in _iter_dict_items(raw_items):
            item = AIRecommendationItem(
                element=raw.get("element"),
                change=raw.get("change"),
                psychological_effect=raw.get("effect")
                or raw.get("psychological_effect"),
                impact=raw.get("impact"),
                priority=(
                    raw.get("priority")
                    or raw.get("type")
                    or raw.get("bucket")
                    or category.lower()
                ),
            )
            items.append(item)
        if items:
            parsed[category] = items
    return parsed


def _format_blocker_for_legacy(category: str, item: DecisionBlockerItem) -> Optional[str]:
    parts = []
    if item.element:
        parts.append(item.element)
    if item.issue:
        parts.append(item.issue)
    if item.psychological_impact:
        parts.append(item.psychological_impact)

    if not parts:
        return None

    summary = " — ".join(parts)
    return f"[{category}] {summary}"


def _format_recommendation_for_legacy(item: AIRecommendationItem) -> Optional[str]:
    if not (item.element or item.change):
        return None

    effect_text = item.psychological_effect or item.impact
    base = f"{item.element or 'Element'}: {item.change or ''}".strip()
    if effect_text:
        return f"{base} ({effect_text})"
    return base


def _to_float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip().replace("%", "")
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_visual_trust_analysis(data: Any) -> Optional[VisualTrustAnalysis]:
    if not isinstance(data, dict):
        return None

    return VisualTrustAnalysis(
        overall_label=_safe_string(data.get("overall_label")),
        low_percent=_to_float_or_none(data.get("low") or data.get("low_percent")),
        medium_percent=_to_float_or_none(
            data.get("medium") or data.get("medium_percent")
        ),
        high_percent=_to_float_or_none(data.get("high") or data.get("high_percent")),
        explanation=_safe_string(data.get("explanation")),
    )


def _parse_psychology_narrative(data: Any) -> Optional[PsychologyNarrative]:
    if not isinstance(data, dict):
        return None

    return PsychologyNarrative(
        analysis_summary=_safe_string(
            data.get("analysis_summary") or data.get("analysisSummary")
        ),
        ai_interpretation=_safe_string(
            data.get("ai_interpretation") or data.get("aiInterpretation")
        ),
    )


def _normalize_result_payload(raw_payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(raw_payload)

    # Map aliases to canonical field names
    for alias, target in _ALIAS_FIELDS.items():
        if alias in payload and target not in payload:
            payload[target] = payload[alias]

    for list_field in _LIST_FIELDS:
        payload[list_field] = _ensure_list(payload.get(list_field))

    friction_value = (
        payload.get("frictionScore")
        or payload.get("decision_friction_score")
        or payload.get("decision_friction")
    )
    payload["frictionScore"] = _coerce_float(friction_value, BASELINE_FRICTION)

    trust_value = payload.get("trustScore") or payload.get("trust_score")
    payload["trustScore"] = _coerce_float(
        trust_value, max(0.0, 100 - payload["frictionScore"])
    )

    payload["emotionalClarityScore"] = _coerce_float(
        payload.get("emotionalClarityScore") or payload.get("emotional_clarity_score"),
        55.0,
    )
    payload["motivationMatchScore"] = _coerce_float(
        payload.get("motivationMatchScore") or payload.get("motivation_match_score"),
        55.0,
    )
    payload["decisionProbability"] = _coerce_float(
        payload.get("decisionProbability") or payload.get("decision_probability"),
        0.45,
    )
    payload["conversionLiftEstimate"] = _coerce_float(
        payload.get("conversionLiftEstimate") or payload.get("conversion_lift_estimate"),
        0.0,
    )

    payload["primary_diagnosis"] = payload.get("primary_diagnosis") or payload.get(
        "primaryDiagnosis"
    )

    summary = (
        payload.get("explanationSummary")
        or payload.get("summary")
        or payload.get("primary_diagnosis")
    )
    payload["explanationSummary"] = summary or "No explanation provided by the model."

    payload["psychology_dashboard"] = _parse_psychology_dashboard(
        payload.get("psychology_dashboard")
    )

    page_structure_raw = (
        payload.get("page_structure")
        or payload.get("page_structure_reconstruction")
        or payload.get("page_structure_map")
    )
    payload["page_structure"] = _normalize_page_structure(page_structure_raw)

    visual_psych = payload.get("visual_textual_psychology_analysis") or payload.get(
        "visual_textual_psychology"
    )
    payload["visual_textual_psychology_analysis"] = (
        visual_psych if isinstance(visual_psych, dict) else None
    )

    decision_blockers_map = _parse_decision_blockers(
        payload.get("decision_blockers") or payload.get("decision_blocker")
    )
    payload["decision_blockers"] = decision_blockers_map

    ai_recommendations_map = _parse_ai_recommendations(
        payload.get("ai_recommendations") or payload.get("AI_recommendations")
    )
    payload["ai_recommendations"] = ai_recommendations_map

    payload["visual_trust_analysis"] = _parse_visual_trust_analysis(
        payload.get("visual_trust_analysis") or payload.get("visual_trust_insights")
    )

    payload["psychology_narrative"] = _parse_psychology_narrative(
        payload.get("psychology_narrative") or payload.get("psychologyNarrative")
    )

    payload["visual_trust_score"] = _to_float_or_none(
        payload.get("visual_trust_score")
        or payload.get("visual_trust_numeric")
        or payload.get("visualTrustScore")
    )

    legacy_blocker_map = {
        "Key Blockers": "keyDecisionBlockers",
        "Emotional Resistance": "emotionalResistanceFactors",
        "Cognitive Overload": "cognitiveOverloadFactors",
        "Trust Breakpoints": "trustBreakpoints",
        "Motivation Gaps": "motivationMisalignments",
        "Motivation Misalignment": "motivationMisalignments",
    }

    for category, target_field in legacy_blocker_map.items():
        formatted_entries = [
            entry
            for entry in (
                _format_blocker_for_legacy(category, item)
                for item in decision_blockers_map.get(category, [])
            )
            if entry
        ]
        if formatted_entries:
            existing = _ensure_list(payload.get(target_field))
            existing.extend(formatted_entries)
            payload[target_field] = existing

    recommendation_targets = {
        "quick wins": "recommendedQuickWins",
        "quick win": "recommendedQuickWins",
        "quick": "recommendedQuickWins",
        "deep changes": "recommendedDeepChanges",
        "deep change": "recommendedDeepChanges",
        "deep": "recommendedDeepChanges",
    }

    for category, items in ai_recommendations_map.items():
        key = category.lower().strip()
        target_field = None
        for matcher, target in recommendation_targets.items():
            if matcher in key:
                target_field = target
                break
        if not target_field:
            continue

        formatted_entries = [
            entry
            for entry in (
                _format_recommendation_for_legacy(item) for item in items
            )
            if entry
        ]
        if formatted_entries:
            existing = _ensure_list(payload.get(target_field))
            existing.extend(formatted_entries)
            payload[target_field] = existing

    return payload


# ====================================================
# 7-FACTOR BEHAVIORAL MODEL HELPERS
# ====================================================


def build_next_better_actions(json_data: Dict[str, Any]) -> List[NextBetterAction]:
    """
    Build NextBetterAction list from LLM JSON response.
    
    Args:
        json_data: Dictionary with "next_better_actions" or "nextBetterActions" key
    
    Returns:
        List of NextBetterAction objects, at least 3 and at most 5
    """
    actions_data = json_data.get("next_better_actions") or json_data.get("nextBetterActions", [])
    
    if not isinstance(actions_data, list):
        logger.warning(f"Expected 'next_better_actions' to be a list, got {type(actions_data)}")
        actions_data = []
    
    actions = []
    seen_ids = set()
    
    for action_data in actions_data:
        try:
            # Validate required fields
            if not isinstance(action_data, dict):
                logger.warning(f"Invalid action data type: {type(action_data)}, skipping")
                continue
            
            action_id = int(action_data.get("id", 0))
            if action_id == 0 or action_id in seen_ids:
                logger.warning(f"Invalid or duplicate action id: {action_id}, skipping")
                continue
            
            seen_ids.add(action_id)
            
            # Extract and validate fields
            title = str(action_data.get("title", "")).strip()
            target_section = str(action_data.get("target_section") or action_data.get("targetSection", "")).strip()
            psychology_label = str(action_data.get("psychology_label") or action_data.get("psychologyLabel", "")).strip()
            problem_summary = str(action_data.get("problem_summary") or action_data.get("problemSummary", "")).strip()
            suggested_change = str(action_data.get("suggested_change") or action_data.get("suggestedChange", "")).strip()
            impact_score = int(action_data.get("impact_score") or action_data.get("impactScore", 50))
            difficulty = int(action_data.get("difficulty", 3))
            priority_rank = int(action_data.get("priority_rank") or action_data.get("priorityRank", action_id))
            
            # Clamp values to valid ranges
            impact_score = max(1, min(100, impact_score))
            difficulty = max(1, min(5, difficulty))
            priority_rank = max(1, priority_rank)
            
            # Validate required fields are not empty
            if not all([title, target_section, psychology_label, problem_summary, suggested_change]):
                logger.warning(f"Action {action_id} missing required fields, skipping")
                continue
            
            action = NextBetterAction(
                id=action_id,
                title=title,
                target_section=target_section,
                psychology_label=psychology_label,
                problem_summary=problem_summary,
                suggested_change=suggested_change,
                impact_score=impact_score,
                difficulty=difficulty,
                priority_rank=priority_rank
            )
            actions.append(action)
        except Exception as e:
            logger.warning(f"Failed to parse action: {action_data}, error: {e}")
            continue
    
    # Sort by priority_rank
    actions.sort(key=lambda a: a.priority_rank)
    
    # Ensure we have at least 3 actions (create defaults if needed)
    if len(actions) < 3:
        logger.warning(f"Only {len(actions)} actions found, expected at least 3. Creating default actions.")
        existing_titles = {a.title.lower() for a in actions}
        existing_ranks = {a.priority_rank for a in actions}
        
        default_actions = [
            {
                "title": "Improve hero headline clarity",
                "target_section": "hero_title",
                "psychology_label": "Cognitive Friction – Ambiguity",
                "problem_summary": "The hero headline may be too abstract or vague.",
                "suggested_change": "Make the headline more specific about the outcome (e.g., 'AI that shows you exactly why visitors don't convert')."
            },
            {
                "title": "Add social proof elements",
                "target_section": "social_proof_section",
                "psychology_label": "Trust Gap – No Proof",
                "problem_summary": "Lack of visible trust signals reduces credibility.",
                "suggested_change": "Add customer testimonials, logos, or case study numbers near the primary CTA."
            },
            {
                "title": "Strengthen primary CTA",
                "target_section": "primary_cta",
                "psychology_label": "Motivation Gap – Weak Urgency",
                "problem_summary": "The call-to-action may not create enough motivation to act.",
                "suggested_change": "Use action-oriented, benefit-focused CTA text (e.g., 'Get Your Free Analysis' instead of 'Learn More')."
            }
        ]
        
        for default_action in default_actions:
            if default_action["title"].lower() not in existing_titles:
                # Find next available rank
                next_rank = max(existing_ranks, default=0) + 1
                existing_ranks.add(next_rank)
                
                action = NextBetterAction(
                    id=next_rank,
                    title=default_action["title"],
                    target_section=default_action["target_section"],
                    psychology_label=default_action["psychology_label"],
                    problem_summary=default_action["problem_summary"],
                    suggested_change=default_action["suggested_change"],
                    impact_score=70,
                    difficulty=2,
                    priority_rank=next_rank
                )
                actions.append(action)
                
                if len(actions) >= 3:
                    break
    
    # Limit to 5 actions max
    actions = actions[:5]
    
    # Re-assign priority_rank sequentially to ensure no gaps
    for idx, action in enumerate(actions, 1):
        action.priority_rank = idx
    
    return actions


def build_behavior_factors(json_data: Dict[str, Any]) -> List[BehaviorFactorScore]:
    """
    Build BehaviorFactorScore list from LLM JSON response.
    
    Args:
        json_data: Dictionary with "factors" key containing list of factor objects
    
    Returns:
        List of BehaviorFactorScore objects
    """
    factors_data = json_data.get("factors", [])
    if not isinstance(factors_data, list):
        logger.warning(f"Expected 'factors' to be a list, got {type(factors_data)}")
        return []
    
    valid_factor_names = {
        "clarity", "trust", "cognitive_effort", "motivation",
        "risk", "memorability", "decision_simplicity"
    }
    
    factors = []
    for factor_data in factors_data:
        try:
            name = factor_data.get("name", "").strip()
            if name not in valid_factor_names:
                logger.warning(f"Invalid factor name: {name}, skipping")
                continue
            
            score = float(factor_data.get("score", 0))
            score = max(0.0, min(100.0, score))  # Clamp to 0-100
            
            # Map score to level
            if score < 50:
                level: Literal["low", "medium", "high"] = "low"
            elif score < 75:
                level = "medium"
            else:
                level = "high"
            
            short_reason = factor_data.get("short_reason", "").strip()
            if not short_reason:
                short_reason = f"{name} score is {score:.0f}"
            
            factor = BehaviorFactorScore(
                name=name,  # type: ignore
                score=score,
                level=level,
                short_reason=short_reason
            )
            factors.append(factor)
        except Exception as e:
            logger.warning(f"Failed to parse factor: {factor_data}, error: {e}")
            continue
    
    # Ensure we have all 7 factors (fill missing ones with defaults)
    existing_names = {f.name for f in factors}
    for required_name in valid_factor_names:
        if required_name not in existing_names:
            logger.warning(f"Missing factor {required_name}, adding default")
            factors.append(BehaviorFactorScore(
                name=required_name,  # type: ignore
                score=50.0,
                level="medium",
                short_reason=f"{required_name} was not evaluated"
            ))
    
    # Sort by name for consistency
    factors.sort(key=lambda f: f.name)
    return factors


def diagnose_behavior(factors: List[BehaviorFactorScore]) -> BehaviorDiagnosis:
    """
    Derive diagnosis from 7 behavioral factor scores.
    
    Args:
        factors: List of 7 BehaviorFactorScore objects
    
    Returns:
        BehaviorDiagnosis with overall_readiness, driver, blocker, risks, quick_win
    """
    if len(factors) != 7:
        logger.warning(f"Expected 7 factors, got {len(factors)}")
    
    # Find strongest_driver: highest score among "high" level factors
    # Prefer clarity/trust/motivation if tied
    high_factors = [f for f in factors if f.level == "high"]
    if high_factors:
        # Sort by score descending, then by preference (lower preference number = higher priority)
        preference_order = {"clarity": 0, "trust": 1, "motivation": 2}
        high_factors.sort(
            key=lambda f: (-f.score, preference_order.get(f.name, 99))
        )
        strongest_driver = high_factors[0]  # Highest score, highest preference
    else:
        # No high factors, use highest score overall
        strongest_driver = max(factors, key=lambda f: f.score)
    
    # Find primary_blocker: lowest score
    # If tied, prefer trust > risk > motivation
    blocker_candidates = [f for f in factors if f.score == min(f.score for f in factors)]
    blocker_preference = {"trust": 0, "risk": 1, "motivation": 2}
    blocker_candidates.sort(key=lambda f: blocker_preference.get(f.name, 99))
    primary_blocker = blocker_candidates[0]
    
    # Find hidden_risk: if risk < 60 OR trust < 60 OR memorability < 60
    risk_factors = [
        f for f in factors
        if f.name in ("risk", "trust", "memorability") and f.score < 60
    ]
    hidden_risk = None
    if risk_factors:
        hidden_risk = min(risk_factors, key=lambda f: f.score)
    
    # Find quick_win: score 50-70, high impact (motivation > memorability > clarity > trust)
    quick_win_candidates = [
        f for f in factors
        if 50 <= f.score <= 70 and f.name in ("motivation", "memorability", "clarity", "trust")
    ]
    quick_win = None
    if quick_win_candidates:
        quick_win_preference = {"motivation": 0, "memorability": 1, "clarity": 2, "trust": 3}
        quick_win_candidates.sort(key=lambda f: quick_win_preference.get(f.name, 99))
        quick_win = quick_win_candidates[0]
    
    # Calculate overall_readiness using weighted composite
    weights = {
        "clarity": 1.0,
        "trust": 1.2,
        "cognitive_effort": -1.0,  # lower is better
        "motivation": 1.0,
        "risk": -1.1,  # lower risk is better
        "memorability": 0.8,
        "decision_simplicity": 0.8,
    }
    
    composite = 0.0
    for factor in factors:
        weight = weights.get(factor.name, 1.0)
        if factor.name in ("cognitive_effort", "risk"):
            # Invert: lower score is better
            composite += weight * (100 - factor.score)
        else:
            composite += weight * factor.score
    
    # Normalize composite (divide by sum of absolute weights)
    total_weight = sum(abs(w) for w in weights.values())
    composite = composite / total_weight if total_weight > 0 else 50.0
    
    # Determine overall_readiness
    trust_factor = next((f for f in factors if f.name == "trust"), None)
    clarity_factor = next((f for f in factors if f.name == "clarity"), None)
    motivation_factor = next((f for f in factors if f.name == "motivation"), None)
    
    if (trust_factor and trust_factor.score < 50) or \
       (clarity_factor and clarity_factor.score < 50) or \
       (motivation_factor and motivation_factor.score < 50):
        overall_readiness: Literal["high", "medium", "low"] = "low"
    elif composite >= 75 and all(f.score >= 60 for f in factors):
        overall_readiness = "high"
    else:
        overall_readiness = "medium"
    
    # Build summary_sentence
    weakness = primary_blocker
    if hidden_risk and hidden_risk.score < weakness.score:
        weakness = hidden_risk
    
    readiness_text = {
        "high": "high",
        "medium": "medium",
        "low": "low"
    }[overall_readiness]
    
    summary_sentence = (
        f"Conversion readiness is {readiness_text}: "
        f"{weakness.short_reason.lower()}"
    )
    
    return BehaviorDiagnosis(
        overall_readiness=overall_readiness,
        summary_sentence=summary_sentence,
        strongest_driver=strongest_driver,
        primary_blocker=primary_blocker,
        hidden_risk=hidden_risk,
        quick_win=quick_win
    )


def build_behavior_recommendations(
    factors: List[BehaviorFactorScore],
    diagnosis: BehaviorDiagnosis
) -> BehaviorRecommendationSet:
    """
    Build behavioral recommendations from factors and diagnosis.
    
    Args:
        factors: List of 7 BehaviorFactorScore objects
        diagnosis: BehaviorDiagnosis object
    
    Returns:
        BehaviorRecommendationSet with primary and secondary recommendations
    """
    # Primary recommendation targets primary_blocker
    blocker = diagnosis.primary_blocker
    
    title_map = {
        "clarity": "Improve clarity",
        "trust": "Strengthen trust signals",
        "cognitive_effort": "Reduce cognitive effort",
        "motivation": "Increase motivation",
        "risk": "Reduce perceived risk",
        "memorability": "Increase memorability",
        "decision_simplicity": "Simplify decision path"
    }
    
    description_map = {
        "clarity": f"Make the value proposition and outcome clearer to reduce {blocker.short_reason.lower()}",
        "trust": f"Add trust signals and proof to address {blocker.short_reason.lower()}",
        "cognitive_effort": f"Simplify the page structure and messaging to reduce {blocker.short_reason.lower()}",
        "motivation": f"Strengthen the value proposition and urgency to address {blocker.short_reason.lower()}",
        "risk": f"Add guarantees, refunds, or risk-reversal elements to address {blocker.short_reason.lower()}",
        "memorability": f"Make the message more distinctive and memorable to address {blocker.short_reason.lower()}",
        "decision_simplicity": f"Streamline the conversion path to address {blocker.short_reason.lower()}"
    }
    
    primary = BehaviorRecommendation(
        title=title_map.get(blocker.name, f"Improve {blocker.name}"),
        description=description_map.get(blocker.name, f"Address {blocker.short_reason.lower()}"),
        target_factors=[blocker.name]  # type: ignore
    )
    
    # Secondary recommendations from hidden_risk and quick_win
    secondary = []
    
    if diagnosis.hidden_risk and diagnosis.hidden_risk.name != blocker.name:
        risk = diagnosis.hidden_risk
        secondary.append(BehaviorRecommendation(
            title=title_map.get(risk.name, f"Address {risk.name} risk"),
            description=description_map.get(risk.name, f"Mitigate {risk.short_reason.lower()}"),
            target_factors=[risk.name]  # type: ignore
        ))
    
    if diagnosis.quick_win and diagnosis.quick_win.name != blocker.name:
        win = diagnosis.quick_win
        if not any(r.target_factors[0] == win.name for r in secondary):
            secondary.append(BehaviorRecommendation(
                title=title_map.get(win.name, f"Optimize {win.name}"),
                description=description_map.get(win.name, f"Quick improvement: {win.short_reason.lower()}"),
                target_factors=[win.name]  # type: ignore
            ))
    
    # Limit to 2 secondary recommendations
    secondary = secondary[:2]
    
    return BehaviorRecommendationSet(
        primary=primary,
        secondary=secondary
    )


# ====================================================
# MAIN ANALYSIS FUNCTION
# ====================================================


# ====================================================
# DECISION OUTCOME TAXONOMY v1.0
# ====================================================

DECISION_OUTCOMES = [
    "OUTCOME_UNCLEAR",
    "RISK_DOMINANT",
    "COGNITIVE_OVERLOAD",
    "IDENTITY_MISMATCH",
    "TRUST_DEBT",
    "EMOTIONAL_DISCONNECT",
    "TIMING_FRICTION",
    "MOTIVATION_CONFLICT"
]


# ====================================================
# CONTEXT INPUT LAYER v1.0
# ====================================================

def infer_context_from_content(
    raw_text: str,
    page_structure: Optional[Dict[str, Any]] = None
) -> Dict[str, Optional[str]]:
    """
    Infer context inputs from page content when not explicitly provided.
    
    Args:
        raw_text: The raw text content
        page_structure: Optional page structure
    
    Returns:
        Dictionary with inferred context values (may be None if cannot infer)
    """
    if not raw_text:
        return {
            "business_type": None,
            "price_level": None,
            "decision_depth": None,
            "user_intent_stage": None,
            "relationship_state": None
        }
    
    text_lower = raw_text.lower()
    inferred = {
        "business_type": None,
        "price_level": None,
        "decision_depth": None,
        "user_intent_stage": None,
        "relationship_state": None
    }
    
    # Infer business_type
    if any(phrase in text_lower for phrase in ["saas", "software", "subscription", "monthly plan", "annual plan"]):
        inferred["business_type"] = "SaaS"
    elif any(phrase in text_lower for phrase in ["add to cart", "buy now", "purchase", "product", "shipping"]):
        inferred["business_type"] = "Ecommerce"
    elif any(phrase in text_lower for phrase in ["clinic", "doctor", "appointment", "healthcare", "medical", "treatment"]):
        inferred["business_type"] = "Clinic / Healthcare"
    elif any(phrase in text_lower for phrase in ["marketplace", "seller", "vendor", "platform"]):
        inferred["business_type"] = "Marketplace"
    elif any(phrase in text_lower for phrase in ["course", "education", "learn", "training", "ebook"]):
        inferred["business_type"] = "Info Product / Education"
    elif any(phrase in text_lower for phrase in ["service", "consulting", "agency"]):
        inferred["business_type"] = "Service Business"
    
    # Infer price_level
    # Look for price patterns
    price_match = re.search(r'\$(\d+)', text_lower)
    if price_match:
        price_value = int(price_match.group(1))
        if price_value < 50:
            inferred["price_level"] = "Low (Impulse)"
        elif price_value < 500:
            inferred["price_level"] = "Medium (Considered)"
        else:
            inferred["price_level"] = "High (High-risk)"
    elif any(phrase in text_lower for phrase in ["free", "trial", "starter"]):
        inferred["price_level"] = "Low (Impulse)"
    elif any(phrase in text_lower for phrase in ["enterprise", "premium", "professional"]):
        inferred["price_level"] = "High (High-risk)"
    
    # Infer decision_depth
    if any(phrase in text_lower for phrase in ["impulse", "quick", "instant", "one-click"]):
        inferred["decision_depth"] = "Impulse"
    elif any(phrase in text_lower for phrase in ["commitment", "contract", "annual", "long-term"]):
        inferred["decision_depth"] = "High-Commitment"
    else:
        inferred["decision_depth"] = "Considered"  # Default
    
    # Infer user_intent_stage
    if any(phrase in text_lower for phrase in ["learn more", "explore", "discover", "about"]):
        inferred["user_intent_stage"] = "Learn"
    elif any(phrase in text_lower for phrase in ["compare", "vs", "versus", "difference"]):
        inferred["user_intent_stage"] = "Compare"
    elif any(phrase in text_lower for phrase in ["testimonial", "review", "proof", "case study"]):
        inferred["user_intent_stage"] = "Validate"
    elif any(phrase in text_lower for phrase in ["buy", "purchase", "order", "get started", "sign up"]):
        inferred["user_intent_stage"] = "Buy"
    
    return inferred


class ContextSnapshot(BaseModel):
    """Context snapshot for decision analysis."""
    
    business_type: Optional[str] = Field(
        default=None,
        description="Business type (SaaS, Ecommerce, Clinic, etc.)."
    )
    price_level: Optional[str] = Field(
        default=None,
        description="Price level (Low/Medium/High)."
    )
    decision_depth: Optional[str] = Field(
        default=None,
        description="Decision depth (Impulse/Considered/High-Commitment)."
    )
    user_intent_stage: Optional[str] = Field(
        default=None,
        description="User intent stage (Learn/Compare/Validate/Buy)."
    )
    relationship_state: Optional[str] = Field(
        default=None,
        description="Relationship state (First-time/Returning/Familiar)."
    )
    confidence_level: Literal["explicit", "inferred", "estimated"] = Field(
        default="estimated",
        description="Confidence level of context (explicit=provided, inferred=detected, estimated=defaulted)."
    )
    missing_context: List[str] = Field(
        default_factory=list,
        description="List of missing required context inputs."
    )
    context_rationale: Optional[str] = Field(
        default=None,
        description="Explanation of why certain outcomes were prioritized based on context."
    )


class OutcomeAnalysis(BaseModel):
    """Structured outcome analysis with confidence and interaction logic."""
    
    primary_outcome: str = Field(
        ...,
        description="Primary decision outcome from taxonomy."
    )
    primary_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for primary outcome (0.00-1.00)."
    )
    secondary_outcome: Optional[str] = Field(
        default=None,
        description="Secondary outcome if confidence < 0.75 and another outcome is close."
    )
    secondary_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score for secondary outcome (0.00-1.00)."
    )
    outcome_interaction: Optional[str] = Field(
        default=None,
        description="Explanation of how primary and secondary outcomes interact psychologically."
    )
    psychological_explanation: str = Field(
        ...,
        description="Why this outcome combination occurs and what breaks in the user's mind."
    )
    priority_fix: str = Field(
        ...,
        description="Which outcome to fix first and why."
    )
    priority_reasoning: str = Field(
        ...,
        description="Reasoning for prioritizing this fix over others."
    )
    is_low_confidence: bool = Field(
        default=False,
        description="True if no outcome reaches 0.6 confidence (multi-factorial state)."
    )
    confidence_factors: Dict[str, Any] = Field(
        default_factory=dict,
        description="Breakdown of confidence factors: signal_strength, context_alignment, competing_outcomes, input_completeness."
    )


def build_context_snapshot(
    input_data: CognitiveFrictionInput,
    raw_text: str,
    page_structure: Optional[Dict[str, Any]] = None
) -> ContextSnapshot:
    """
    Build context snapshot from explicit inputs or inferred values.
    
    Args:
        input_data: Input data with optional context fields
        raw_text: Raw text content for inference
        page_structure: Optional page structure
    
    Returns:
        ContextSnapshot with explicit, inferred, or estimated values
    """
    # Get explicit context
    explicit_context = {
        "business_type": input_data.business_type,
        "price_level": input_data.price_level,
        "decision_depth": input_data.decision_depth,
        "user_intent_stage": input_data.user_intent_stage,
        "relationship_state": input_data.relationship_state
    }
    
    # Infer missing context
    inferred_context = infer_context_from_content(raw_text, page_structure)
    
    # Combine: explicit takes precedence
    final_context = {}
    missing_context = []
    confidence_level = "explicit"
    
    for key in ["business_type", "price_level", "decision_depth", "user_intent_stage", "relationship_state"]:
        if explicit_context[key]:
            final_context[key] = explicit_context[key]
        elif inferred_context[key]:
            final_context[key] = inferred_context[key]
            if confidence_level == "explicit":
                confidence_level = "inferred"
        else:
            final_context[key] = None
            if key != "relationship_state":  # relationship_state is optional
                missing_context.append(key)
            if confidence_level != "estimated":
                confidence_level = "estimated"
    
    # Check if ≥2 required context inputs are missing
    required_fields = ["business_type", "price_level", "decision_depth", "user_intent_stage"]
    missing_required = [f for f in required_fields if final_context[f] is None]
    
    if len(missing_required) >= 2:
        logger.warning(f"Missing {len(missing_required)} required context inputs: {missing_required}")
        confidence_level = "estimated"
    
    return ContextSnapshot(
        business_type=final_context["business_type"],
        price_level=final_context["price_level"],
        decision_depth=final_context["decision_depth"],
        user_intent_stage=final_context["user_intent_stage"],
        relationship_state=final_context["relationship_state"],
        confidence_level=confidence_level,  # type: ignore
        missing_context=missing_required
    )


def apply_context_weighting_to_outcomes(
    outcome_scores: Dict[str, float],
    context: ContextSnapshot
) -> Dict[str, float]:
    """
    Apply context-based weighting to outcome scores.
    
    Args:
        outcome_scores: Dictionary of outcome scores
        context: Context snapshot
    
    Returns:
        Weighted outcome scores
    """
    weighted_scores = outcome_scores.copy()
    
    # High price + first-time visitor → increase RISK_DOMINANT, TRUST_DEBT
    if (context.price_level == "High (High-risk)" and 
        context.relationship_state == "First-time visitor"):
        weighted_scores["RISK_DOMINANT"] *= 1.5
        weighted_scores["TRUST_DEBT"] *= 1.4
        logger.info("Context weighting: High price + first-time visitor → increased RISK_DOMINANT and TRUST_DEBT")
    
    # Learn intent → suppress BUY-focused CTAs, increase TIMING_FRICTION
    if context.user_intent_stage == "Learn":
        weighted_scores["TIMING_FRICTION"] *= 1.6
        weighted_scores["OUTCOME_UNCLEAR"] *= 0.8  # Less likely if learning
        logger.info("Context weighting: Learn intent → increased TIMING_FRICTION")
    
    # Clinic / Healthcare → elevate TRUST_DEBT sensitivity
    if context.business_type == "Clinic / Healthcare":
        weighted_scores["TRUST_DEBT"] *= 1.5
        weighted_scores["RISK_DOMINANT"] *= 1.3
        logger.info("Context weighting: Clinic/Healthcare → increased TRUST_DEBT and RISK_DOMINANT")
    
    # Impulse product → suppress COGNITIVE_OVERLOAD, elevate OUTCOME_UNCLEAR
    if context.decision_depth == "Impulse":
        weighted_scores["COGNITIVE_OVERLOAD"] *= 0.7
        weighted_scores["OUTCOME_UNCLEAR"] *= 1.3
        logger.info("Context weighting: Impulse decision → decreased COGNITIVE_OVERLOAD, increased OUTCOME_UNCLEAR")
    
    # High-Commitment → increase RISK_DOMINANT, MOTIVATION_CONFLICT
    if context.decision_depth == "High-Commitment":
        weighted_scores["RISK_DOMINANT"] *= 1.4
        weighted_scores["MOTIVATION_CONFLICT"] *= 1.3
        logger.info("Context weighting: High-Commitment → increased RISK_DOMINANT and MOTIVATION_CONFLICT")
    
    # Compare intent → increase COGNITIVE_OVERLOAD, TIMING_FRICTION
    if context.user_intent_stage == "Compare":
        weighted_scores["COGNITIVE_OVERLOAD"] *= 1.3
        weighted_scores["TIMING_FRICTION"] *= 1.4
        logger.info("Context weighting: Compare intent → increased COGNITIVE_OVERLOAD and TIMING_FRICTION")
    
    # Validate intent → increase TRUST_DEBT sensitivity
    if context.user_intent_stage == "Validate":
        weighted_scores["TRUST_DEBT"] *= 1.3
        logger.info("Context weighting: Validate intent → increased TRUST_DEBT")
    
    # Returning visitor → decrease TRUST_DEBT, increase TIMING_FRICTION
    if context.relationship_state == "Returning visitor":
        weighted_scores["TRUST_DEBT"] *= 0.7
        weighted_scores["TIMING_FRICTION"] *= 1.2
        logger.info("Context weighting: Returning visitor → decreased TRUST_DEBT, increased TIMING_FRICTION")
    
    # Familiar / Brand-aware → decrease TRUST_DEBT significantly
    if context.relationship_state == "Familiar / Brand-aware":
        weighted_scores["TRUST_DEBT"] *= 0.5
        weighted_scores["TIMING_FRICTION"] *= 1.3
        logger.info("Context weighting: Familiar visitor → significantly decreased TRUST_DEBT, increased TIMING_FRICTION")
    
    return weighted_scores


def generate_context_rationale(
    primary_outcome: str,
    context: ContextSnapshot
) -> str:
    """
    Generate explanation of why certain outcomes were prioritized based on context.
    
    Args:
        primary_outcome: The detected primary outcome
        context: Context snapshot
    
    Returns:
        Rationale string explaining context-based prioritization
    """
    rationale_parts = []
    
    if context.business_type:
        rationale_parts.append(f"Business type ({context.business_type})")
    
    if context.price_level:
        rationale_parts.append(f"price level ({context.price_level})")
    
    if context.decision_depth:
        rationale_parts.append(f"decision depth ({context.decision_depth})")
    
    if context.user_intent_stage:
        rationale_parts.append(f"user intent ({context.user_intent_stage})")
    
    if context.relationship_state:
        rationale_parts.append(f"relationship state ({context.relationship_state})")
    
    if rationale_parts:
        context_str = ", ".join(rationale_parts)
        return (
            f"Primary outcome ({primary_outcome}) was prioritized based on context: {context_str}. "
            f"Context confidence: {context.confidence_level}."
        )
    else:
        return f"Primary outcome ({primary_outcome}) detected. Context confidence: {context.confidence_level}."


def calculate_confidence_factors(
    outcome_scores: Dict[str, float],
    context: Optional[ContextSnapshot],
    raw_text: str,
    decision_blockers: Optional[Dict[str, List[DecisionBlockerItem]]]
) -> Dict[str, Any]:
    """
    Calculate confidence factors: signal strength, context alignment, competing outcomes, input completeness.
    
    Args:
        outcome_scores: Dictionary of outcome scores
        context: Context snapshot
        raw_text: Raw text content
        decision_blockers: Optional decision blockers
    
    Returns:
        Dictionary with confidence factor breakdown
    """
    factors = {
        "signal_strength": 0.0,
        "context_alignment": 0.0,
        "competing_outcomes": 0.0,
        "input_completeness": 0.0
    }
    
    # Signal strength: based on how clear the primary signal is
    sorted_scores = sorted(outcome_scores.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_scores) > 0:
        primary_score = sorted_scores[0][1]
        if len(sorted_scores) > 1:
            secondary_score = sorted_scores[1][1]
            # Signal strength is higher if primary clearly dominates
            score_gap = primary_score - secondary_score
            factors["signal_strength"] = min(1.0, score_gap / max(primary_score, 0.1))
        else:
            factors["signal_strength"] = 1.0 if primary_score > 0 else 0.0
    
    # Context alignment: based on context quality
    if context:
        if context.confidence_level == "explicit":
            factors["context_alignment"] = 1.0
        elif context.confidence_level == "inferred":
            factors["context_alignment"] = 0.7
        else:  # estimated
            factors["context_alignment"] = 0.4
    else:
        factors["context_alignment"] = 0.3
    
    # Competing outcomes: lower confidence if multiple outcomes are close
    if len(sorted_scores) > 1:
        top_2_gap = sorted_scores[0][1] - sorted_scores[1][1]
        # If gap is small, competing outcomes reduce confidence
        if top_2_gap < 0.2:
            factors["competing_outcomes"] = 0.3  # High competition
        elif top_2_gap < 0.4:
            factors["competing_outcomes"] = 0.6  # Medium competition
        else:
            factors["competing_outcomes"] = 1.0  # Low competition
    else:
        factors["competing_outcomes"] = 1.0
    
    # Input completeness: based on available inputs
    completeness = 0.5  # Base score
    if raw_text and len(raw_text) > 100:
        completeness += 0.2
    if decision_blockers:
        completeness += 0.2
    if context and context.confidence_level != "estimated":
        completeness += 0.1
    factors["input_completeness"] = min(1.0, completeness)
    
    return factors


def detect_outcome_interaction(
    primary_outcome: str,
    secondary_outcome: Optional[str]
) -> Optional[str]:
    """
    Detect and explain how two outcomes interact psychologically.
    
    Args:
        primary_outcome: Primary outcome
        secondary_outcome: Secondary outcome (if present)
    
    Returns:
        Explanation of outcome interaction, or None if no secondary outcome
    """
    if not secondary_outcome:
        return None
    
    interaction_map = {
        ("RISK_DOMINANT", "TRUST_DEBT"): (
            "Risk perception is amplified by low trust. The user fears loss, "
            "and without trust signals, that fear becomes overwhelming."
        ),
        ("TRUST_DEBT", "RISK_DOMINANT"): (
            "Low trust amplifies risk perception. The user fears loss, "
            "and without trust signals, that fear becomes overwhelming."
        ),
        ("COGNITIVE_OVERLOAD", "OUTCOME_UNCLEAR"): (
            "Complexity masks the final outcome. Too much information prevents "
            "the user from understanding what they'll actually receive."
        ),
        ("OUTCOME_UNCLEAR", "COGNITIVE_OVERLOAD"): (
            "Unclear outcomes combined with information overload create decision paralysis. "
            "The user can't see the destination, and the path is too complex."
        ),
        ("TIMING_FRICTION", "MOTIVATION_CONFLICT"): (
            "User is not ready to decide and internally conflicted. They need time "
            "to resolve internal contradictions before committing."
        ),
        ("MOTIVATION_CONFLICT", "TIMING_FRICTION"): (
            "Internal conflict makes the user defer decision. They're not ready "
            "because they haven't resolved competing motivations."
        ),
        ("TRUST_DEBT", "RISK_DOMINANT"): (
            "Low credibility makes risk feel unmanageable. Without trust, "
            "even moderate risks feel too high."
        ),
        ("EMOTIONAL_DISCONNECT", "IDENTITY_MISMATCH"): (
            "User doesn't see themselves in the message, so emotional connection fails. "
            "The story doesn't resonate because it's not their story."
        ),
        ("IDENTITY_MISMATCH", "EMOTIONAL_DISCONNECT"): (
            "Generic messaging prevents emotional connection. The user can't feel "
            "the value because they don't see themselves reflected."
        ),
    }
    
    # Check both orderings
    key1 = (primary_outcome, secondary_outcome)
    key2 = (secondary_outcome, primary_outcome)
    
    if key1 in interaction_map:
        return interaction_map[key1]
    elif key2 in interaction_map:
        return interaction_map[key2]
    else:
        # Generic interaction explanation
        return (
            f"{primary_outcome.replace('_', ' ').title()} and {secondary_outcome.replace('_', ' ').title()} "
            f"interact to create compound decision friction. Both must be addressed for effective resolution."
        )


def detect_decision_outcome(
    raw_text: str,
    page_structure: Optional[Dict[str, Any]] = None,
    decision_blockers: Optional[Dict[str, List[DecisionBlockerItem]]] = None,
    context: Optional[ContextSnapshot] = None
) -> OutcomeAnalysis:
    """
    Detect decision outcomes with confidence scoring and multi-outcome handling.
    
    Args:
        raw_text: The raw text content of the page
        page_structure: Optional page structure dict with detected elements
        decision_blockers: Optional decision blockers already detected
        context: Optional context snapshot
    
    Returns:
        OutcomeAnalysis with primary/secondary outcomes, confidence scores, and interaction logic
    """
    if not raw_text:
        return OutcomeAnalysis(
            primary_outcome="OUTCOME_UNCLEAR",
            primary_confidence=0.5,
            secondary_outcome=None,
            secondary_confidence=None,
            outcome_interaction=None,
            psychological_explanation="Insufficient content to analyze decision failure.",
            priority_fix="OUTCOME_UNCLEAR",
            priority_reasoning="Cannot determine fix priority without content.",
            is_low_confidence=True,
            confidence_factors={
                "signal_strength": 0.0,
                "context_alignment": 0.3,
                "competing_outcomes": 1.0,
                "input_completeness": 0.2
            }
        )
    
    text_lower = raw_text.lower()
    
    # Score each outcome based on indicators
    outcome_scores = {
        "OUTCOME_UNCLEAR": 0.0,
        "RISK_DOMINANT": 0.0,
        "COGNITIVE_OVERLOAD": 0.0,
        "IDENTITY_MISMATCH": 0.0,
        "TRUST_DEBT": 0.0,
        "EMOTIONAL_DISCONNECT": 0.0,
        "TIMING_FRICTION": 0.0,
        "MOTIVATION_CONFLICT": 0.0
    }
    
    # OUTCOME_UNCLEAR indicators
    if any(phrase in text_lower for phrase in ["unclear", "vague", "what happens", "what will", "not sure what"]):
        outcome_scores["OUTCOME_UNCLEAR"] += 0.3
    if not any(phrase in text_lower for phrase in ["you will", "you get", "receive", "after", "then"]):
        outcome_scores["OUTCOME_UNCLEAR"] += 0.2
    
    # RISK_DOMINANT indicators
    risk_phrases = ["risk", "guarantee", "refund", "money back", "safe", "secure", "warranty", "protection"]
    if any(phrase in text_lower for phrase in risk_phrases):
        outcome_scores["RISK_DOMINANT"] += 0.2
    # High price or commitment
    if re.search(r'\$\d{3,}', text_lower) or any(phrase in text_lower for phrase in ["annual", "yearly", "commitment", "contract"]):
        outcome_scores["RISK_DOMINANT"] += 0.3
    
    # COGNITIVE_OVERLOAD indicators
    if len(text_lower.split()) > 500:  # Dense copy
        outcome_scores["COGNITIVE_OVERLOAD"] += 0.2
    if text_lower.count("feature") > 5 or text_lower.count("benefit") > 5:
        outcome_scores["COGNITIVE_OVERLOAD"] += 0.3
    # Multiple CTAs
    cta_count = text_lower.count("button") + text_lower.count("click") + text_lower.count("cta")
    if cta_count > 3:
        outcome_scores["COGNITIVE_OVERLOAD"] += 0.2
    
    # IDENTITY_MISMATCH indicators
    generic_phrases = ["everyone", "all users", "anyone", "universal", "one size fits all"]
    if any(phrase in text_lower for phrase in generic_phrases):
        outcome_scores["IDENTITY_MISMATCH"] += 0.3
    if not any(phrase in text_lower for phrase in ["for", "designed for", "perfect for", "ideal for"]):
        outcome_scores["IDENTITY_MISMATCH"] += 0.2
    
    # TRUST_DEBT indicators
    if not any(phrase in text_lower for phrase in ["trusted", "proven", "testimonial", "review", "rating", "customer"]):
        outcome_scores["TRUST_DEBT"] += 0.3
    if any(phrase in text_lower for phrase in ["new", "launching", "beta", "coming soon"]):
        outcome_scores["TRUST_DEBT"] += 0.2
    
    # EMOTIONAL_DISCONNECT indicators
    emotional_phrases = ["feel", "emotion", "passion", "excited", "inspired", "motivated"]
    if not any(phrase in text_lower for phrase in emotional_phrases):
        outcome_scores["EMOTIONAL_DISCONNECT"] += 0.3
    if all(phrase not in text_lower for phrase in ["story", "journey", "transform", "change"]):
        outcome_scores["EMOTIONAL_DISCONNECT"] += 0.2
    
    # TIMING_FRICTION indicators
    if any(phrase in text_lower for phrase in ["compare", "learn more", "explore", "browse"]):
        outcome_scores["TIMING_FRICTION"] += 0.2
    if any(phrase in text_lower for phrase in ["limited time", "act now", "hurry", "expires"]):
        outcome_scores["TIMING_FRICTION"] += 0.3
    
    # MOTIVATION_CONFLICT indicators (harder to detect from text alone, but check for hesitation signals)
    if any(phrase in text_lower for phrase in ["but", "however", "although", "despite"]):
        outcome_scores["MOTIVATION_CONFLICT"] += 0.2
    
    # Check decision blockers if provided
    if decision_blockers:
        for category, items in decision_blockers.items():
            for item in items:
                issue_lower = (item.issue or "").lower()
                impact_lower = (item.psychological_impact or "").lower()
                
                # Map old blocker names to new outcomes
                if "trust" in issue_lower or "trust" in impact_lower:
                    outcome_scores["TRUST_DEBT"] += 0.2
                if "risk" in issue_lower or "risk" in impact_lower:
                    outcome_scores["RISK_DOMINANT"] += 0.2
                if "overload" in issue_lower or "too many" in issue_lower or "complex" in issue_lower:
                    outcome_scores["COGNITIVE_OVERLOAD"] += 0.2
                if "emotional" in issue_lower or "feeling" in issue_lower:
                    outcome_scores["EMOTIONAL_DISCONNECT"] += 0.2
    
    # Apply context weighting if context is provided
    if context:
        outcome_scores = apply_context_weighting_to_outcomes(outcome_scores, context)
        logger.info(f"Applied context weighting: business_type={context.business_type}, price_level={context.price_level}, intent={context.user_intent_stage}")
    
    # Calculate confidence factors
    confidence_factors = calculate_confidence_factors(outcome_scores, context, raw_text, decision_blockers)
    
    # Find primary outcome
    sorted_outcomes = sorted(outcome_scores.items(), key=lambda x: x[1], reverse=True)
    primary_outcome = sorted_outcomes[0][0]
    primary_score = sorted_outcomes[0][1]
    
    # Calculate primary confidence using weighted factors
    base_confidence = min(1.0, primary_score / max(sum(outcome_scores.values()), 0.1))
    # Weight confidence by factors
    primary_confidence = (
        base_confidence * 0.4 +  # Base score
        confidence_factors["signal_strength"] * 0.25 +
        confidence_factors["context_alignment"] * 0.2 +
        confidence_factors["competing_outcomes"] * 0.1 +
        confidence_factors["input_completeness"] * 0.05
    )
    primary_confidence = min(1.0, max(0.0, primary_confidence))
    
    # Determine secondary outcome based on confidence rules
    secondary_outcome = None
    secondary_confidence = None
    is_low_confidence = primary_confidence < 0.6
    
    # Rule 2: Secondary outcome if confidence < 0.75 and another outcome is close
    if primary_confidence < 0.75 and len(sorted_outcomes) > 1:
        secondary_score = sorted_outcomes[1][1]
        score_gap = primary_score - secondary_score
        # If secondary is within 40% of primary, include it
        if score_gap < (primary_score * 0.4) and secondary_score > 0:
            secondary_outcome = sorted_outcomes[1][0]
            # Secondary confidence is lower than primary
            secondary_confidence = primary_confidence * 0.7
            logger.info(f"Secondary outcome detected: {secondary_outcome} (confidence: {secondary_confidence:.2f})")
    
    # Detect outcome interaction
    outcome_interaction = detect_outcome_interaction(primary_outcome, secondary_outcome)
    
    # Generate psychological explanation
    if is_low_confidence:
        psychological_explanation = (
            "Decision failure appears multi-factorial. Multiple psychological barriers are present, "
            "making it difficult to identify a single dominant cause. Additional context may be needed."
        )
    elif secondary_outcome:
        psychological_explanation = (
            f"The user's decision failure is primarily caused by {primary_outcome.replace('_', ' ').lower()}, "
            f"but {secondary_outcome.replace('_', ' ').lower()} also contributes significantly. "
            f"{outcome_interaction or 'Both factors interact to create compound friction.'}"
        )
    else:
        psychological_explanation = (
            f"The user's decision failure is primarily caused by {primary_outcome.replace('_', ' ').lower()}. "
            f"This is the dominant psychological barrier preventing commitment."
        )
    
    # Determine priority fix
    # Generally, fix the primary outcome first, but if secondary is very close, consider both
    if secondary_outcome and secondary_confidence and (primary_confidence - secondary_confidence) < 0.15:
        priority_fix = f"{primary_outcome} and {secondary_outcome}"
        priority_reasoning = (
            f"Both outcomes are nearly equally dominant. Address {primary_outcome.replace('_', ' ').lower()} first "
            f"as it has slightly higher confidence ({primary_confidence:.2f} vs {secondary_confidence:.2f}), "
            f"but {secondary_outcome.replace('_', ' ').lower()} should be addressed simultaneously."
        )
    else:
        priority_fix = primary_outcome
        priority_reasoning = (
            f"Address {primary_outcome.replace('_', ' ').lower()} first because it is the dominant barrier "
            f"(confidence: {primary_confidence:.2f}). "
            + (f"Then address {secondary_outcome.replace('_', ' ').lower()}." if secondary_outcome else "")
        )
    
    logger.info(
        f"Decision outcome analysis: primary={primary_outcome} ({primary_confidence:.2f}), "
        f"secondary={secondary_outcome} ({secondary_confidence or 'N/A'}), "
        f"low_confidence={is_low_confidence}"
    )
    
    return OutcomeAnalysis(
        primary_outcome=primary_outcome,
        primary_confidence=primary_confidence,
        secondary_outcome=secondary_outcome,
        secondary_confidence=secondary_confidence,
        outcome_interaction=outcome_interaction,
        psychological_explanation=psychological_explanation,
        priority_fix=priority_fix,
        priority_reasoning=priority_reasoning,
        is_low_confidence=is_low_confidence,
        confidence_factors=confidence_factors
    )


def transform_blockers_to_outcomes(
    decision_blockers: Dict[str, List[DecisionBlockerItem]],
    primary_outcome: str
) -> Dict[str, List[DecisionBlockerItem]]:
    """
    Transform old blocker names to align with Decision Outcome Taxonomy.
    
    Args:
        decision_blockers: Dictionary of blocker categories to items
        primary_outcome: The detected primary outcome from taxonomy
    
    Returns:
        Transformed decision blockers dictionary
    """
    # Mapping from old blocker names to new outcomes
    blocker_to_outcome_map = {
        "outcome unclear": "OUTCOME_UNCLEAR",
        "trust gap": "TRUST_DEBT",
        "low trust": "TRUST_DEBT",
        "risk not addressed": "RISK_DOMINANT",
        "effort too high": "COGNITIVE_OVERLOAD",
        "commitment anxiety": "RISK_DOMINANT",
        "decision overload": "COGNITIVE_OVERLOAD",
        "trust anxiety": "RISK_DOMINANT",
        "fear of wrong choice": "RISK_DOMINANT",
    }
    
    transformed = {}
    
    for category, items in decision_blockers.items():
        transformed_items = []
        for item in items:
            issue_lower = (item.issue or "").lower()
            
            # Transform blocker names to match taxonomy
            for old_name, new_outcome in blocker_to_outcome_map.items():
                if old_name in issue_lower:
                    # Update issue to reference new outcome
                    item.issue = item.issue.replace(old_name.title(), new_outcome.replace("_", " ").title())
                    logger.info(f"Transformed blocker '{old_name}' to outcome '{new_outcome}'")
                    break
            
            transformed_items.append(item)
        
        if transformed_items:
            transformed[category] = transformed_items
    
    return transformed


class OutcomeRecommendationSet(BaseModel):
    """Structured recommendations for a specific outcome, split into 3 layers."""
    
    message_level: List[str] = Field(
        ...,
        description="Message-level recommendations: copy, language, framing changes."
    )
    structure_level: List[str] = Field(
        ...,
        description="Structure-level recommendations: layout, hierarchy, information architecture changes."
    )
    timing_level: List[str] = Field(
        default_factory=list,
        description="Timing-level recommendations: when to show elements, pacing, commitment timing."
    )
    psychological_goal: str = Field(
        ...,
        description="The psychological goal this outcome addresses."
    )
    intervention_strategy: str = Field(
        ...,
        description="The overall intervention strategy for this outcome."
    )


def generate_outcome_specific_recommendations(
    outcome: str,
    raw_text: str,
    page_structure: Optional[Dict[str, Any]] = None
) -> OutcomeRecommendationSet:
    """
    Generate outcome-specific recommendations with 3-layer structure (Message, Structure, Timing).
    
    Each outcome has distinct intervention logic, recommendation categories, and psychological goals.
    Recommendations are phrased as actions, not advice.
    
    Args:
        outcome: One of DECISION_OUTCOMES
        raw_text: The raw text content
        page_structure: Optional page structure
    
    Returns:
        OutcomeRecommendationSet with structured recommendations
    """
    
    if outcome == "OUTCOME_UNCLEAR":
        return OutcomeRecommendationSet(
            psychological_goal="Clarify the future state after decision",
            intervention_strategy="Make the post-decision experience explicit and tangible",
            message_level=[
                "Rewrite headline to state explicit outcome: 'You will receive [specific thing]'",
                "Add before/after framing: 'Before: [current state]. After: [future state]'",
                "Replace vague benefits with concrete deliverables: 'Get [X] that does [Y]'",
                "Use expectation-setting language: 'Here's exactly what happens next'"
            ],
            structure_level=[
                "Move outcome statement above the fold in hero section",
                "Create simplified benefit hierarchy: primary outcome → secondary benefits",
                "Add visual before/after comparison if applicable",
                "Place outcome clarity before feature lists"
            ],
            timing_level=[
                "Show outcome immediately (no delay tactics)",
                "Present future state before asking for commitment",
                "Avoid progressive disclosure for core outcome"
            ]
        )
    
    elif outcome == "RISK_DOMINANT":
        return OutcomeRecommendationSet(
            psychological_goal="Reduce perceived downside without inflating upside",
            intervention_strategy="Build safety net and reduce loss perception",
            message_level=[
                "Add risk reversal language: '100% money-back guarantee' or 'No risk, full refund'",
                "Include reassurance phrases: 'Safe to try', 'Cancel anytime', 'No commitment'",
                "Emphasize loss minimization: 'Nothing to lose', 'Risk-free trial'",
                "Use safety framing: 'Protected by [trust signal]', 'Secure payment'"
            ],
            structure_level=[
                "Place guarantees and safety cues before the CTA",
                "Add proof elements (testimonials, certifications) before pricing",
                "Create dedicated 'Safety & Guarantee' section above fold",
                "Show refund/return policy prominently, not in footer"
            ],
            timing_level=[
                "Slow decision pacing: allow time to read safety information",
                "Show reassurance before asking for commitment",
                "Delay CTA until trust and safety signals are consumed",
                "Avoid urgency triggers that increase risk perception"
            ]
        )
    
    elif outcome == "COGNITIVE_OVERLOAD":
        return OutcomeRecommendationSet(
            psychological_goal="Lower mental effort required to decide",
            intervention_strategy="Simplify decision path and reduce cognitive load",
            message_level=[
                "Reduce claims to top 3 most important benefits",
                "Remove jargon and technical language",
                "Use clear prioritization: 'Most important: [X]'",
                "Eliminate redundant or overlapping messages"
            ],
            structure_level=[
                "Create single decision path: one primary CTA, remove secondary options",
                "Chunk information into digestible sections with clear headings",
                "Use progressive disclosure: show basics first, details on demand",
                "Reduce visual clutter: white space, clear hierarchy"
            ],
            timing_level=[
                "Reveal information progressively, not all at once",
                "Show core value first, details later",
                "Allow user to control information flow (expandable sections)",
                "Avoid overwhelming with simultaneous information"
            ]
        )
    
    elif outcome == "IDENTITY_MISMATCH":
        return OutcomeRecommendationSet(
            psychological_goal="Signal 'this is for people like you'",
            intervention_strategy="Align messaging and visuals with target persona",
            message_level=[
                "Use persona-specific language that matches target audience",
                "Add identity cues: 'For [specific role/persona]', 'Built for [user type]'",
                "Include relatable scenarios: 'If you [specific situation], then...'",
                "Replace generic messaging with targeted positioning"
            ],
            structure_level=[
                "Show visual alignment with target persona (images, design style)",
                "Place identity confirmation above the fold",
                "Create narrative that reflects target user's identity",
                "Use tone and style that matches persona expectations"
            ],
            timing_level=[
                "Confirm identity match early (above the fold)",
                "Show persona alignment before features or pricing",
                "Establish 'this is for you' signal before asking for action"
            ]
        )
    
    elif outcome == "TRUST_DEBT":
        return OutcomeRecommendationSet(
            psychological_goal="Accumulate credibility before asking for commitment",
            intervention_strategy="Build trust through evidence and authority",
            message_level=[
                "Add evidence-backed claims: 'Used by [X] companies', 'Trusted by [Y] users'",
                "Include authority language: 'Industry leader', 'Award-winning', 'Certified'",
                "Use specific proof: '10,000+ customers', '4.9/5 rating', 'Featured in [media]'",
                "Replace unsubstantiated claims with verifiable facts"
            ],
            structure_level=[
                "Sequence proof strategically: logos → testimonials → case studies → guarantees",
                "Create credibility stacking: layer multiple trust signals",
                "Place trust elements before CTA, not after",
                "Show social proof prominently (above fold if possible)"
            ],
            timing_level=[
                "Delay CTA until trust signals are consumed",
                "Show credibility before asking for commitment",
                "Build trust progressively: start with strongest signal",
                "Avoid pushing urgency before trust is established"
            ]
        )
    
    elif outcome == "EMOTIONAL_DISCONNECT":
        return OutcomeRecommendationSet(
            psychological_goal="Activate emotional motivation",
            intervention_strategy="Connect with user's emotional state and desires",
            message_level=[
                "Add emotional framing: 'Feel [emotion]', 'Experience [feeling]'",
                "Include narrative hooks: stories, scenarios, relatable moments",
                "Use motivation triggers: 'Imagine...', 'Picture yourself...'",
                "Replace logical features with emotional benefits"
            ],
            structure_level=[
                "Create story-driven layout: narrative flow, not feature list",
                "Add relatable scenarios and use cases",
                "Use visuals that evoke emotion (not just product shots)",
                "Structure content as journey, not specification sheet"
            ],
            timing_level=[
                "Build emotional peak before CTA",
                "Show emotional connection before logical details",
                "Create emotional momentum leading to decision point",
                "Avoid interrupting emotional flow with technical information"
            ]
        )
    
    elif outcome == "TIMING_FRICTION":
        return OutcomeRecommendationSet(
            psychological_goal="Allow safe deferral without losing the user",
            intervention_strategy="Remove pressure while maintaining engagement",
            message_level=[
                "Use low-pressure language: 'Explore', 'Learn more', 'See how it works'",
                "Remove urgency triggers: 'Limited time', 'Act now', 'Hurry'",
                "Add deferral-friendly CTAs: 'Save for later', 'Get started when ready'",
                "Include comparison-friendly language: 'Compare options', 'See all plans'"
            ],
            structure_level=[
                "Create soft CTAs: secondary actions, not primary commitment",
                "Add reminder paths: 'Email me details', 'Send me a guide'",
                "Include bookmark/save functionality if applicable",
                "Show comparison tools or decision guides"
            ],
            timing_level=[
                "Provide follow-up hooks: email capture, reminder options",
                "Allow delayed commitment: 'Start free trial anytime'",
                "Create multiple touchpoints, not single pressure point",
                "Enable deferred decision without losing context"
            ]
        )
    
    elif outcome == "MOTIVATION_CONFLICT":
        return OutcomeRecommendationSet(
            psychological_goal="Resolve internal contradiction",
            intervention_strategy="Clarify value hierarchy and address trade-offs",
            message_level=[
                "Clarify value hierarchy: 'Most important benefit: [X]'",
                "Add trade-off framing: 'Choose [A] if you value [X], choose [B] if you value [Y]'",
                "Include priority cues: 'Focus on [primary value]'",
                "Address both rational and emotional needs explicitly"
            ],
            structure_level=[
                "Create comparison framing: side-by-side value propositions",
                "Add priority cues: visual hierarchy showing what matters most",
                "Include decision aids: 'Which option fits you?' guides",
                "Show value alignment: how product matches user's priorities"
            ],
            timing_level=[
                "Provide decision pause: 'Take your time', 'No rush'",
                "Allow reframing: 'Still deciding? Here's what to consider'",
                "Create reflection space before commitment",
                "Enable value clarification before asking for action"
            ]
        )
    
    else:
        # Fallback for unknown outcomes
        return OutcomeRecommendationSet(
            psychological_goal="Address decision friction",
            intervention_strategy="Improve clarity and reduce hesitation",
            message_level=["Clarify value proposition and expected outcomes"],
            structure_level=["Simplify decision path and information hierarchy"],
            timing_level=[]
        )


# ====================================================
# MARKETPLACE DETECTION & VALIDATION
# ====================================================

def detect_saas_pricing_page(
    raw_text: str,
    page_structure: Optional[Dict[str, Any]] = None
) -> Tuple[bool, bool]:
    """
    Detect if the page is a SaaS pricing page with multiple plans.
    
    Args:
        raw_text: The raw text content of the page
        page_structure: Optional page structure dict with detected elements
    
    Returns:
        Tuple of (is_saas_pricing, has_multiple_plans)
    """
    if not raw_text:
        return False, False
    
    text_lower = raw_text.lower()
    
    # SaaS pricing indicators
    pricing_keywords = [
        "pricing", "plan", "tier", "package", "subscription",
        "monthly", "annual", "per month", "per year",
        "starter", "professional", "enterprise", "basic", "premium",
        "free trial", "start free", "get started"
    ]
    
    # Check for multiple plans (look for plan names, tiers, or pricing cards)
    plan_indicators = [
        r"(?:plan|tier|package)\s*(?:1|2|3|one|two|three|i|ii|iii)",
        r"(?:starter|basic|professional|enterprise|premium)",
        r"\$\d+.*\$\d+",  # Multiple prices
        r"(?:monthly|annual).*(?:monthly|annual)",  # Multiple billing options
    ]
    
    has_pricing_keywords = any(keyword in text_lower for keyword in pricing_keywords)
    has_multiple_plans = any(re.search(pattern, text_lower, re.I) for pattern in plan_indicators)
    
    # Check page structure if available
    if page_structure:
        pricing_section = page_structure.get("pricing_section", "")
        if isinstance(pricing_section, str) and pricing_section:
            pricing_lower = pricing_section.lower()
            has_pricing_keywords = has_pricing_keywords or any(kw in pricing_lower for kw in pricing_keywords)
            # Count plan mentions in pricing section
            plan_count = sum(1 for pattern in plan_indicators if re.search(pattern, pricing_lower, re.I))
            if plan_count >= 2:
                has_multiple_plans = True
    
    # Also check for SaaS-specific CTAs
    saas_ctas = ["start free", "free trial", "get started", "sign up", "try free"]
    has_saas_cta = any(cta in text_lower for cta in saas_ctas)
    
    is_saas_pricing = has_pricing_keywords and (has_saas_cta or has_multiple_plans)
    
    if is_saas_pricing:
        logger.info("SaaS pricing page detected: has_pricing=%s, has_multiple_plans=%s, has_saas_cta=%s",
                   has_pricing_keywords, has_multiple_plans, has_saas_cta)
    
    return is_saas_pricing, has_multiple_plans


def filter_saas_pricing_blockers(
    decision_blockers: Dict[str, List[DecisionBlockerItem]],
    is_saas_pricing: bool,
    has_multiple_plans: bool
) -> Dict[str, List[DecisionBlockerItem]]:
    """
    Filter and prioritize decision blockers for SaaS pricing pages.
    Replaces generic "Outcome Unclear" with "Decision Overload" or "Plan-to-Outcome Unclear" when appropriate.
    
    Args:
        decision_blockers: Dictionary of blocker categories to items
        is_saas_pricing: Whether this is a SaaS pricing page
        has_multiple_plans: Whether multiple plans are detected
    
    Returns:
        Filtered decision blockers dictionary
    """
    if not is_saas_pricing:
        return decision_blockers
    
    filtered = {}
    
    for category, items in decision_blockers.items():
        filtered_items = []
        for item in items:
            issue_lower = (item.issue or "").lower()
            element_lower = (item.element or "").lower()
            impact_lower = (item.psychological_impact or "").lower()
            
            # If multiple plans detected, replace generic "Outcome Unclear" with more specific blockers
            if has_multiple_plans:
                # Check if this is a generic "Outcome Unclear" blocker
                is_generic_outcome_unclear = any(
                    phrase in issue_lower or phrase in impact_lower
                    for phrase in [
                        "outcome unclear", "outcome is unclear", "unclear outcome",
                        "vague outcome", "unclear what", "doesn't understand what"
                    ]
                ) and not any(
                    phrase in issue_lower or phrase in impact_lower
                    for phrase in [
                        "plan", "tier", "package", "which plan", "choose plan",
                        "decision overload", "too many options"
                    ]
                )
                
                if is_generic_outcome_unclear:
                    # Check if it's about plan selection (Decision Overload) or plan outcomes (Plan-to-Outcome Unclear)
                    if any(phrase in issue_lower or phrase in impact_lower
                           for phrase in ["choose", "select", "pick", "which", "too many", "overwhelming"]):
                        # Transform to Decision Overload
                        logger.info(f"Transforming generic 'Outcome Unclear' to 'Decision Overload': {item.issue}")
                        item.issue = (item.issue or "").replace("Outcome Unclear", "Decision Overload")
                        item.psychological_impact = (
                            (item.psychological_impact or "") + 
                            " Fear of choosing wrong plan and uncertainty about which plan fits which team/scale/goal."
                        )
                    else:
                        # Transform to Plan-to-Outcome Unclear
                        logger.info(f"Transforming generic 'Outcome Unclear' to 'Plan-to-Outcome Unclear': {item.issue}")
                        item.issue = (item.issue or "").replace("Outcome Unclear", "Plan-to-Outcome Unclear")
                        item.psychological_impact = (
                            (item.psychological_impact or "") + 
                            " Unclear which plan fits which team size, scale, or goal."
                        )
            
            filtered_items.append(item)
        
        if filtered_items:
            filtered[category] = filtered_items
    
    return filtered


def filter_saas_pricing_recommendations(
    recommendations: Dict[str, List[AIRecommendationItem]],
    is_saas_pricing: bool
) -> Dict[str, List[AIRecommendationItem]]:
    """
    Filter AI recommendations for SaaS pricing pages.
    Ensures recommendations focus on plan clarity, not analysis-tool CTAs.
    
    Args:
        recommendations: Dictionary of recommendation categories to items
        is_saas_pricing: Whether this is a SaaS pricing page
    
    Returns:
        Filtered recommendations dictionary
    """
    if not is_saas_pricing:
        return recommendations
    
    forbidden_phrases = [
        "know exactly why users don't decide",
        "decision diagnosis",
        "analysis tool",
        "conversion diagnosis",
        "see the one reason"
    ]
    
    preferred_phrases = [
        "best for",
        "choose this if",
        "plan description",
        "outcome-based",
        "decision guide"
    ]
    
    filtered = {}
    
    for category, items in recommendations.items():
        filtered_items = []
        for item in items:
            change_lower = (item.change or "").lower()
            element_lower = (item.element or "").lower()
            
            # Skip recommendations with forbidden analysis-tool phrases
            if any(phrase in change_lower or phrase in element_lower for phrase in forbidden_phrases):
                logger.info(f"Filtered out analysis-tool recommendation: {item.change}")
                continue
            
            # Prioritize recommendations with preferred SaaS pricing phrases
            if any(phrase in change_lower for phrase in preferred_phrases):
                filtered_items.insert(0, item)  # Add to front
            else:
                filtered_items.append(item)
        
        if filtered_items:
            filtered[category] = filtered_items
    
    return filtered


def detect_service_clinic_page(
    raw_text: str,
    page_structure: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Detect if the page is a service/clinic/appointment booking page.
    
    Args:
        raw_text: The raw text content of the page
        page_structure: Optional page structure dict with detected elements
    
    Returns:
        True if detected as service/clinic page, False otherwise
    """
    if not raw_text:
        return False
    
    text_lower = raw_text.lower()
    
    # Appointment booking CTAs
    booking_cta_patterns = [
        "book appointment",
        "schedule",
        "reserve",
        "book now",
        "schedule appointment",
        "book a visit",
        "make appointment",
        "رزرو نوبت",
        "نوبت گیری",
        "رزرو",
        "ثبت نوبت"
    ]
    
    # Service/clinic indicators
    service_indicators = [
        "appointment", "booking", "provider", "doctor", "physician",
        "consultant", "specialist", "clinic", "practice", "medical",
        "healthcare", "service", "treatment", "consultation",
        "پزشک", "دکتر", "کلینیک", "خدمات", "درمان"
    ]
    
    # Check for appointment booking UI
    has_booking_cta = any(pattern in text_lower for pattern in booking_cta_patterns)
    
    # Check for provider profile signals
    provider_signals = [
        "profile", "doctor", "physician", "provider", "specialist",
        "credentials", "experience", "education", "board certified",
        "پروفایل", "تجربه", "مدرک"
    ]
    has_provider_profile = any(signal in text_lower for signal in provider_signals)
    
    # Check for ratings/reviews
    rating_signals = [
        "rating", "review", "star", "patient review", "testimonial",
        "امتیاز", "نظر", "نظرات بیماران"
    ]
    has_ratings = any(signal in text_lower for signal in rating_signals)
    
    # Check for service indicators
    has_service_indicators = any(indicator in text_lower for indicator in service_indicators)
    
    # Check page structure if available
    if page_structure:
        primary_cta = page_structure.get("primary_cta", "").lower() if isinstance(page_structure.get("primary_cta"), str) else ""
        if any(pattern in primary_cta for pattern in booking_cta_patterns):
            has_booking_cta = True
        
        social_proof = page_structure.get("social_proof_section", "")
        if isinstance(social_proof, str) and social_proof:
            if any(signal in social_proof.lower() for signal in rating_signals):
                has_ratings = True
    
    # Service/clinic detection: booking CTA AND (provider profile OR ratings OR service indicators)
    is_service_clinic = has_booking_cta and (has_provider_profile or has_ratings or has_service_indicators)
    
    if is_service_clinic:
        logger.info("Service/clinic page detected: has_booking_cta=%s, has_provider=%s, has_ratings=%s, has_service=%s",
                   has_booking_cta, has_provider_profile, has_ratings, has_service_indicators)
    
    return is_service_clinic


def filter_service_clinic_blockers(
    decision_blockers: Dict[str, List[DecisionBlockerItem]],
    is_service_clinic: bool
) -> Dict[str, List[DecisionBlockerItem]]:
    """
    Filter decision blockers for service/clinic pages.
    Removes "Outcome Unclear" blockers and prioritizes emotionally-driven blockers.
    
    Args:
        decision_blockers: Dictionary of blocker categories to items
        is_service_clinic: Whether this is a service/clinic page
    
    Returns:
        Filtered decision blockers dictionary
    """
    if not is_service_clinic:
        return decision_blockers
    
    filtered = {}
    
    # Preferred emotional blockers for service/clinic pages
    preferred_blockers = [
        "trust anxiety",
        "fear of wrong choice",
        "perceived personal risk",
        "post-booking uncertainty",
        "trust gap",
        "risk not addressed"
    ]
    
    for category, items in decision_blockers.items():
        filtered_items = []
        for item in items:
            issue_lower = (item.issue or "").lower()
            element_lower = (item.element or "").lower()
            impact_lower = (item.psychological_impact or "").lower()
            
            # Remove "Outcome Unclear" blockers
            is_outcome_unclear = any(
                phrase in issue_lower or phrase in impact_lower
                for phrase in [
                    "outcome unclear", "outcome is unclear", "unclear outcome",
                    "vague outcome", "unclear what", "doesn't understand what"
                ]
            )
            
            if is_outcome_unclear:
                logger.info(f"Filtered out 'Outcome Unclear' blocker from service/clinic page: {item.issue}")
                continue
            
            # Enhance emotional blockers with WHY rules
            issue_lower_check = issue_lower
            if any(preferred in issue_lower_check for preferred in ["trust anxiety", "fear of wrong choice"]):
                # Ensure WHY references emotional risk, personal consequences, reassurance needs
                current_impact = item.psychological_impact or ""
                if not any(phrase in current_impact.lower() 
                          for phrase in ["emotional risk", "personal consequence", "reassurance", "fear", "anxiety"]):
                    item.psychological_impact = (
                        current_impact + 
                        " Emotional risk and personal consequences create hesitation. Reassurance about provider fit and next steps is needed."
                    )
                    logger.info(f"Enhanced emotional blocker WHY: {item.issue}")
            
            filtered_items.append(item)
        
        if filtered_items:
            filtered[category] = filtered_items
    
    return filtered


def filter_service_clinic_recommendations(
    recommendations: Dict[str, List[AIRecommendationItem]],
    is_service_clinic: bool
) -> Dict[str, List[AIRecommendationItem]]:
    """
    Filter AI recommendations for service/clinic pages.
    Ensures recommendations focus on reassurance and risk reduction, not analytical CTAs.
    
    Args:
        recommendations: Dictionary of recommendation categories to items
        is_service_clinic: Whether this is a service/clinic page
    
    Returns:
        Filtered recommendations dictionary
    """
    if not is_service_clinic:
        return recommendations
    
    forbidden_phrases = [
        "know exactly why users don't decide",
        "decision diagnosis",
        "analysis tool",
        "conversion diagnosis",
        "see the one reason",
        "free trial",
        "sign up",
        "get started"
    ]
    
    preferred_phrases = [
        "reassurance",
        "risk reduction",
        "next steps",
        "what to expect",
        "explanation",
        "trust",
        "guarantee",
        "safety"
    ]
    
    filtered = {}
    
    for category, items in recommendations.items():
        filtered_items = []
        for item in items:
            change_lower = (item.change or "").lower()
            element_lower = (item.element or "").lower()
            
            # Skip recommendations with forbidden analytical/SaaS phrases
            if any(phrase in change_lower or phrase in element_lower for phrase in forbidden_phrases):
                logger.info(f"Filtered out analytical recommendation from service/clinic page: {item.change}")
                continue
            
            # Prioritize recommendations with preferred service/clinic phrases
            if any(phrase in change_lower for phrase in preferred_phrases):
                filtered_items.insert(0, item)  # Add to front
            else:
                filtered_items.append(item)
        
        if filtered_items:
            filtered[category] = filtered_items
    
    return filtered


def detect_marketplace_product_page(
    raw_text: str,
    page_structure: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Detect if the page is a marketplace product page.
    
    Args:
        raw_text: The raw text content of the page
        page_structure: Optional page structure dict with detected elements
    
    Returns:
        True if detected as marketplace product page, False otherwise
    """
    if not raw_text:
        return False
    
    text_lower = raw_text.lower()
    
    # Marketplace CTA patterns
    marketplace_cta_patterns = [
        "add to cart",
        "افزودن به سبد",
        "buy now",
        "خرید",
        "افزودن به سبد خرید",
        "add to basket",
        "افزودن",
        "خرید آنلاین",
        "order now",
        "purchase",
        "خریداری"
    ]
    
    # Check for price patterns
    price_patterns = [
        r'\$\d+[\d,.]*',  # $99.99
        r'\d+[\d,.]*\s*(?:TL|TRY|USD|EUR|£|تومان|ریال)',  # 99.99 TL or تومان
        r'(?:price|cost|fee|قیمت)[:\s]*\$?\d+',  # Price: $99
    ]
    
    has_price = any(re.search(pattern, text_lower, re.I) for pattern in price_patterns)
    
    # Check for marketplace CTAs
    has_marketplace_cta = any(pattern in text_lower for pattern in marketplace_cta_patterns)
    
    # Check for product-specific signals
    product_signals = [
        "review", "rating", "star", "امتیاز", "نظرات",
        "spec", "specification", "مشخصات",
        "warranty", "guarantee", "ضمانت",
        "delivery", "shipping", "ارسال",
        "return", "refund", "بازگشت"
    ]
    
    has_product_signals = any(signal in text_lower for signal in product_signals)
    
    # Check page structure if available
    if page_structure:
        primary_cta = page_structure.get("primary_cta", "").lower() if isinstance(page_structure.get("primary_cta"), str) else ""
        if any(pattern in primary_cta for pattern in marketplace_cta_patterns):
            has_marketplace_cta = True
    
    # Marketplace detection: price AND (marketplace CTA OR product signals)
    is_marketplace = has_price and (has_marketplace_cta or has_product_signals)
    
    if is_marketplace:
        logger.info("Marketplace product page detected: has_price=%s, has_cta=%s, has_signals=%s", 
                   has_price, has_marketplace_cta, has_product_signals)
    
    return is_marketplace


def filter_marketplace_blockers(
    decision_blockers: Dict[str, List[DecisionBlockerItem]],
    is_marketplace: bool,
    primary_outcome: Optional[str] = None
) -> Dict[str, List[DecisionBlockerItem]]:
    """
    Filter decision blockers for marketplace products.
    Removes "Outcome Unclear" blockers and prioritizes trust-related blockers.
    
    Args:
        decision_blockers: Dictionary of blocker categories to items
        is_marketplace: Whether this is a marketplace product page
    
    Returns:
        Filtered decision blockers dictionary
    """
    if not is_marketplace:
        return decision_blockers
    
    filtered = {}
    
    for category, items in decision_blockers.items():
        filtered_items = []
        for item in items:
            # Remove "Outcome Unclear" blockers
            issue_lower = (item.issue or "").lower()
            element_lower = (item.element or "").lower()
            impact_lower = (item.psychological_impact or "").lower()
            
            # Check if this blocker mentions "Outcome Unclear" or similar
            if any(phrase in issue_lower or phrase in impact_lower 
                   for phrase in ["outcome unclear", "outcome is unclear", "unclear outcome", 
                                  "vague outcome", "unclear what", "doesn't understand what"]):
                logger.info(f"Filtered out 'Outcome Unclear' blocker from category '{category}': {item.issue}")
                continue
            
            # Keep trust-related blockers
            filtered_items.append(item)
        
        if filtered_items:
            filtered[category] = filtered_items
    
    return filtered


def filter_marketplace_recommendations(
    recommendations: Dict[str, List[AIRecommendationItem]],
    is_marketplace: bool
) -> Dict[str, List[AIRecommendationItem]]:
    """
    Filter AI recommendations for marketplace products.
    Removes SaaS-style CTAs and analytical language.
    
    Args:
        recommendations: Dictionary of recommendation categories to items
        is_marketplace: Whether this is a marketplace product page
    
    Returns:
        Filtered recommendations dictionary
    """
    if not is_marketplace:
        return recommendations
    
    forbidden_phrases = [
        "know exactly why users don't decide",
        "decision diagnosis",
        "analysis tool",
        "conversion diagnosis",
        "see the one reason",
        "free trial",
        "sign up",
        "get started",
        "learn more about",
        "analyze",
        "diagnosis"
    ]
    
    filtered = {}
    
    for category, items in recommendations.items():
        filtered_items = []
        for item in recommendations[category]:
            change_lower = (item.change or "").lower()
            element_lower = (item.element or "").lower()
            
            # Skip recommendations with forbidden SaaS/analytical phrases
            if any(phrase in change_lower or phrase in element_lower for phrase in forbidden_phrases):
                logger.info(f"Filtered out SaaS-style recommendation: {item.change}")
                continue
            
            # Keep marketplace-appropriate recommendations
            filtered_items.append(item)
        
        if filtered_items:
            filtered[category] = filtered_items
    
    return filtered


def analyze_cognitive_friction(
    input_data: CognitiveFrictionInput,
    *,
    image_base64: Optional[str] = None,
    image_mime: Optional[str] = None,
    image_score: Optional[float] = None,
    model_override: Optional[str] = None,
    temperature: float = 0.1,
) -> CognitiveFrictionResult:
    """
    Run the cognitive friction engine for the provided input.

    Args:
        input_data: Structured request payload.
        image_base64: Optional base64-encoded screenshot/photo to analyze.
        image_mime: MIME type for the base64 payload.
        image_score: Optional numeric score from the visual trust model.
        model_override: Use a fine-tuned model instead of the default brain.
        temperature: LLM sampling temperature.
    """

    textual_payload = _build_user_text_payload(input_data, image_score=image_score)
    user_content = _build_user_message_content(textual_payload, image_base64, image_mime)

    # Extract context fields from input_data or meta
    url = input_data.meta.get("url") if input_data.meta else None
    page_type = input_data.meta.get("page_type") if input_data.meta else None
    business_type = input_data.business_type
    price_level = input_data.price_level
    decision_depth = input_data.decision_depth
    user_intent = input_data.user_intent_stage
    page_copy = input_data.raw_text or ""

    # Log input parameters before calling LLM
    logger.info(
        f"[CF ENGINE] Input url={url}, page_type={page_type}, "
        f"business_type={business_type}, price_level={price_level}, "
        f"decision_depth={decision_depth}, user_intent={user_intent}"
    )
    logger.info(f"[CF ENGINE] Page copy length={len(page_copy)}")

    logger.info(
        "Using Cognitive Friction system prompt (first 120 chars): %s",
        COGNITIVE_FRICTION_SYSTEM_PROMPT[:120],
    )

    messages = [
        {"role": "system", "content": COGNITIVE_FRICTION_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    logger.info(
        "[cognitive_friction] Calling OpenAI (model=%s, has_image=%s, text_length=%d)",
        model_override or "gpt-4o-mini",
        bool(image_base64),
        len(input_data.raw_text or ""),
    )

    client = get_client()
    try:
        response = client.chat.completions.create(
            model=model_override or "gpt-4o-mini",
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=messages,
        )
    except Exception as exc:
        logger.exception("OpenAI API call failed: %s", exc)
        raise

    raw_output = response.choices[0].message.content if response.choices else ""
    
    # Log raw LLM response immediately after receiving it
    logger.info(f"[CF ENGINE] Raw LLM response: {raw_output}")
    if not raw_output:
        raise InvalidAIResponseError("Empty response from model", raw_output or "")

    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        logger.error("Model returned non-JSON payload: %s", raw_output[:200])
        raise InvalidAIResponseError("Model response was not valid JSON.", raw_output) from exc

    normalized = _normalize_result_payload(payload)
    
    # 🧠 CONTEXT INPUT LAYER v1.0 - Build context snapshot
    context_snapshot = build_context_snapshot(
        input_data=input_data,
        raw_text=input_data.raw_text or "",
        page_structure=normalized.get("page_structure")
    )
    
    # Log context status
    if context_snapshot.missing_context:
        logger.warning(f"Missing context inputs: {context_snapshot.missing_context}. Confidence: {context_snapshot.confidence_level}")
    
    # 🧠 DECISION OUTCOME TAXONOMY v1.0 - Core cognitive logic
    # Try to read primary_outcome, confidence, what_to_fix_first from parsed JSON first
    # If not available, use detect_decision_outcome as fallback
    parsed_primary_outcome = None
    parsed_confidence = None
    parsed_what_to_fix_first = None
    parsed_recommendations = None
    
    # Try to read from top-level payload first
    if "primary_outcome" in payload:
        parsed_primary_outcome = payload.get("primary_outcome")
        logger.info(f"[CF ENGINE] Found primary_outcome in parsed JSON: {parsed_primary_outcome}")
    if "confidence" in payload:
        parsed_confidence = float(payload.get("confidence", 0.0))
        logger.info(f"[CF ENGINE] Found confidence in parsed JSON: {parsed_confidence}")
    if "what_to_fix_first" in payload:
        parsed_what_to_fix_first = payload.get("what_to_fix_first")
        logger.info(f"[CF ENGINE] Found what_to_fix_first in parsed JSON: {parsed_what_to_fix_first}")
    if "recommendations" in payload:
        parsed_recommendations = payload.get("recommendations")
        logger.info(f"[CF ENGINE] Found recommendations in parsed JSON")
    
    # If we have primary_outcome from parsed JSON, use it; otherwise use detect_decision_outcome
    if parsed_primary_outcome:
        # Use parsed values from LLM
        outcome_analysis = OutcomeAnalysis(
            primary_outcome=parsed_primary_outcome.upper().replace(" ", "_"),
            primary_confidence=parsed_confidence if parsed_confidence is not None else 0.7,
            secondary_outcome=None,
            secondary_confidence=None,
            outcome_interaction=None,
            psychological_explanation=f"The decision failure is primarily caused by {parsed_primary_outcome.lower()}.",
            priority_fix=parsed_what_to_fix_first if parsed_what_to_fix_first else parsed_primary_outcome,
            priority_reasoning=f"Address {parsed_primary_outcome.lower()} first based on LLM analysis.",
            is_low_confidence=parsed_confidence is not None and parsed_confidence < 0.6,
            confidence_factors={
                "signal_strength": parsed_confidence if parsed_confidence is not None else 0.7,
                "context_alignment": 0.8,
                "competing_outcomes": 0.3,
                "input_completeness": 0.9
            }
        )
        logger.info(f"[CF ENGINE] Using primary_outcome from parsed JSON: {parsed_primary_outcome}")
    else:
        # Fallback to detect_decision_outcome
        logger.info(f"[CF ENGINE] primary_outcome not found in parsed JSON, using detect_decision_outcome")
        outcome_analysis = detect_decision_outcome(
            raw_text=input_data.raw_text or "",
            page_structure=normalized.get("page_structure"),
            decision_blockers=normalized.get("decision_blockers"),
            context=context_snapshot
        )
    
    # Generate context rationale
    context_rationale = generate_context_rationale(outcome_analysis.primary_outcome, context_snapshot)
    context_snapshot.context_rationale = context_rationale
    
    # Transform blockers to align with new taxonomy
    if normalized.get("decision_blockers"):
        normalized["decision_blockers"] = transform_blockers_to_outcomes(
            normalized["decision_blockers"],
            outcome_analysis.primary_outcome
        )
        logger.info(f"Transformed blockers to align with outcome taxonomy: {outcome_analysis.primary_outcome}")
    
    # Store outcome analysis and context in metadata
    if "metadata" not in normalized:
        normalized["metadata"] = {}
    normalized["metadata"]["primary_outcome"] = outcome_analysis.primary_outcome
    normalized["metadata"]["primary_confidence"] = outcome_analysis.primary_confidence
    if outcome_analysis.secondary_outcome:
        normalized["metadata"]["secondary_outcome"] = outcome_analysis.secondary_outcome
        normalized["metadata"]["secondary_confidence"] = outcome_analysis.secondary_confidence
    normalized["metadata"]["outcome_interaction"] = outcome_analysis.outcome_interaction
    normalized["metadata"]["psychological_explanation"] = outcome_analysis.psychological_explanation
    normalized["metadata"]["priority_fix"] = outcome_analysis.priority_fix
    normalized["metadata"]["priority_reasoning"] = outcome_analysis.priority_reasoning
    normalized["metadata"]["is_low_confidence"] = outcome_analysis.is_low_confidence
    normalized["metadata"]["confidence_factors"] = outcome_analysis.confidence_factors
    # Store context snapshot
    normalized["metadata"]["context_snapshot"] = context_snapshot.dict()
    # Store full outcome analysis
    normalized["metadata"]["outcome_analysis"] = outcome_analysis.dict()
    
    # Detect SaaS pricing page
    is_saas_pricing, has_multiple_plans = detect_saas_pricing_page(
        raw_text=input_data.raw_text or "",
        page_structure=normalized.get("page_structure")
    )
    
    # Detect service/clinic page
    is_service_clinic = detect_service_clinic_page(
        raw_text=input_data.raw_text or "",
        page_structure=normalized.get("page_structure")
    )
    
    # Detect marketplace product page
    is_marketplace = detect_marketplace_product_page(
        raw_text=input_data.raw_text or "",
        page_structure=normalized.get("page_structure")
    )
    
    # Filter decision blockers for SaaS pricing pages (prioritize Decision Overload over generic Outcome Unclear)
    if is_saas_pricing and normalized.get("decision_blockers"):
        normalized["decision_blockers"] = filter_saas_pricing_blockers(
            normalized["decision_blockers"],
            is_saas_pricing=True,
            has_multiple_plans=has_multiple_plans
        )
        logger.info(f"Filtered decision blockers for SaaS pricing page (multiple_plans={has_multiple_plans})")
    
    # Filter AI recommendations for SaaS pricing pages
    if is_saas_pricing and normalized.get("ai_recommendations"):
        normalized["ai_recommendations"] = filter_saas_pricing_recommendations(
            normalized["ai_recommendations"],
            is_saas_pricing=True
        )
        logger.info("Filtered AI recommendations for SaaS pricing page")
    
    # Filter decision blockers for marketplace products (remove "Outcome Unclear")
    if is_marketplace and normalized.get("decision_blockers"):
        normalized["decision_blockers"] = filter_marketplace_blockers(
            normalized["decision_blockers"],
            is_marketplace=True,
            primary_outcome=outcome_analysis.primary_outcome
        )
        logger.info(f"Filtered decision blockers for marketplace product page (outcome: {outcome_analysis.primary_outcome})")
    
    # Filter AI recommendations for marketplace products (remove SaaS-style CTAs)
    if is_marketplace and normalized.get("ai_recommendations"):
        normalized["ai_recommendations"] = filter_marketplace_recommendations(
            normalized["ai_recommendations"],
            is_marketplace=True
        )
        logger.info("Filtered AI recommendations for marketplace product page")
    
    # Filter decision blockers for service/clinic pages (remove "Outcome Unclear", prioritize emotional blockers)
    if is_service_clinic and normalized.get("decision_blockers"):
        normalized["decision_blockers"] = filter_service_clinic_blockers(
            normalized["decision_blockers"],
            is_service_clinic=True
        )
        logger.info("Filtered decision blockers for service/clinic page")
    
    # Filter AI recommendations for service/clinic pages
    if is_service_clinic and normalized.get("ai_recommendations"):
        normalized["ai_recommendations"] = filter_service_clinic_recommendations(
            normalized["ai_recommendations"],
            is_service_clinic=True
        )
        logger.info("Filtered AI recommendations for service/clinic page")
    
    # Remove behavior_factors from normalized if present, since we build it properly later
    # The raw data from LLM doesn't have the 'level' field required by BehaviorFactorScore
    normalized.pop("behavior_factors", None)
    normalized.pop("behaviorFactors", None)
    
    # For next_better_actions, we need to provide an empty list as placeholder
    # because Pydantic v2 requires the field to be present in the dict
    # We'll rebuild it properly after creating the result object
    normalized.pop("next_better_actions", None)
    normalized.pop("nextBetterActions", None)
    normalized["next_better_actions"] = []  # Placeholder empty list

    result = CognitiveFrictionResult(**normalized)
    result.raw_model_output = raw_output
    # Merge outcome metadata with existing metadata
    base_metadata = {
        "model": model_override or "gpt-4o-mini",
        "has_image": bool(image_base64),
        "image_mime": image_mime,
        "image_score": image_score,
    }
    # Preserve outcome taxonomy metadata from normalized
    if normalized.get("metadata"):
        base_metadata.update(normalized["metadata"])
    result.metadata = base_metadata

    if result.psychology_dashboard is None:
        result.psychology_dashboard = build_psychology_dashboard_stub(
            friction_score=result.frictionScore,
            trust_score=result.trustScore,
        )

    # Build 7-factor behavioral model
    try:
        behavior_factors_data = payload.get("behavior_factors") or payload.get("behaviorFactors")
        if behavior_factors_data:
            # build_behavior_factors expects {"factors": [...]}
            behavior_factors = build_behavior_factors({"factors": behavior_factors_data})
            if len(behavior_factors) == 7:
                result.behavior_factors = behavior_factors
                
                # Build diagnosis
                diagnosis = diagnose_behavior(behavior_factors)
                result.behavior_diagnosis = diagnosis
                
                # Build recommendations
                recommendations = build_behavior_recommendations(behavior_factors, diagnosis)
                result.behavior_recommendations = recommendations
                
                logger.info(
                    f"Behavioral analysis completed: readiness={diagnosis.overall_readiness}, "
                    f"driver={diagnosis.strongest_driver.name}, blocker={diagnosis.primary_blocker.name}"
                )
            else:
                logger.warning(f"Expected 7 behavior factors, got {len(behavior_factors)}")
        else:
            logger.info("No behavior_factors in LLM response, skipping behavioral analysis")
    except Exception as e:
        logger.warning(f"Failed to build behavioral analysis: {e}", exc_info=True)
        # Don't fail the entire request if behavioral analysis fails

    # Build next_better_actions (required field, must always be populated)
    try:
        next_better_actions = build_next_better_actions(payload)
        
        # 🧠 OUTCOME → RECOMMENDATION MAPPING v1.0
        # Generate structured recommendations with 3 layers (Message, Structure, Timing)
        outcome_rec_set = generate_outcome_specific_recommendations(
            outcome_analysis.primary_outcome,
            input_data.raw_text or "",
            normalized.get("page_structure")
        )
        
        # Store outcome intervention strategy in metadata
        if "metadata" not in normalized:
            normalized["metadata"] = {}
        normalized["metadata"]["outcome_intervention_strategy"] = outcome_rec_set.intervention_strategy
        normalized["metadata"]["outcome_psychological_goal"] = outcome_rec_set.psychological_goal
        
        # Check if existing actions are generic or outcome-agnostic
        generic_indicators = ["improve", "enhance", "better", "optimize", "consider", "think about"]
        has_generic_actions = any(
            any(indicator in (action.title or "").lower() or indicator in (action.suggested_change or "").lower()
                for indicator in generic_indicators)
            for action in next_better_actions
        )
        
        # If actions are too generic, replace/enhance with outcome-specific recommendations
        if has_generic_actions:
            logger.info(f"Enhancing generic actions with outcome-specific recommendations for {outcome_analysis.primary_outcome}")
            logger.info(f"Intervention strategy: {outcome_rec_set.intervention_strategy}")
            logger.info(f"Psychological goal: {outcome_rec_set.psychological_goal}")
            
            # Collect all outcome-specific recommendations (prioritize message-level, then structure, then timing)
            all_outcome_recs = []
            
            # Message-level recommendations (highest priority)
            for rec in outcome_rec_set.message_level[:2]:  # Top 2 message-level
                all_outcome_recs.append(("message", rec))
            
            # Structure-level recommendations
            for rec in outcome_rec_set.structure_level[:2]:  # Top 2 structure-level
                all_outcome_recs.append(("structure", rec))
            
            # Timing-level recommendations (if available)
            if outcome_rec_set.timing_level:
                for rec in outcome_rec_set.timing_level[:1]:  # Top 1 timing-level
                    all_outcome_recs.append(("timing", rec))
            
            # Replace generic actions with outcome-specific ones
            outcome_actions = []
            for idx, (layer, rec) in enumerate(all_outcome_recs[:5], 1):  # Max 5 outcome-specific actions
                # Check if similar recommendation already exists
                if not any(rec.lower() in (action.suggested_change or "").lower() 
                          for action in next_better_actions):
                    # Determine target section based on layer
                    if layer == "message":
                        target_section = "hero_title" if idx == 1 else "primary_cta"
                    elif layer == "structure":
                        target_section = "pricing" if idx <= 2 else "hero_title"
                    else:  # timing
                        target_section = "primary_cta"
                    
                    # Create action with outcome context
                    new_action = NextBetterAction(
                        id=len(next_better_actions) + idx,
                        title=f"{outcome_analysis.primary_outcome.replace('_', ' ').title()} — {layer.title()}-Level Fix",
                        target_section=target_section,
                        psychology_label=f"{outcome_analysis.primary_outcome.replace('_', ' ').title()} ({layer.title()})",
                        problem_summary=(
                            f"Psychological goal: {outcome_rec_set.psychological_goal}. "
                            f"Intervention: {outcome_rec_set.intervention_strategy}. "
                            f"This {layer}-level change addresses the {outcome_analysis.primary_outcome.replace('_', ' ').lower()} outcome. "
                            f"Confidence: {outcome_analysis.primary_confidence:.2f}."
                        ),
                        suggested_change=rec,
                        impact_score=90 if layer == "message" else 85 if layer == "structure" else 80,
                        difficulty=2 if layer == "message" else 3 if layer == "structure" else 2,
                        priority_rank=idx
                    )
                    outcome_actions.append(new_action)
            
            # If we have outcome-specific actions, prioritize them
            if outcome_actions:
                # Keep non-generic existing actions, but prioritize outcome-specific ones
                non_generic_existing = [
                    action for action in next_better_actions
                    if not any(indicator in (action.title or "").lower() or indicator in (action.suggested_change or "").lower()
                              for indicator in generic_indicators)
                ]
                # Combine: outcome-specific first, then non-generic existing
                next_better_actions = outcome_actions + non_generic_existing
                # Limit to 5 total
                next_better_actions = next_better_actions[:5]
        
        # Limit to 5 actions max
        next_better_actions = next_better_actions[:5]
        # Re-assign priority_rank sequentially
        for idx, action in enumerate(next_better_actions, 1):
            action.priority_rank = idx
        
        # Filter SaaS pricing-inappropriate actions
        if is_saas_pricing:
            filtered_actions = []
            forbidden_phrases = [
                "know exactly why users don't decide",
                "decision diagnosis",
                "analysis tool",
                "conversion diagnosis",
                "see the one reason"
            ]
            
            preferred_phrases = [
                "best for",
                "choose this if",
                "plan description",
                "outcome-based",
                "decision guide"
            ]
            
            for action in next_better_actions:
                suggested_change_lower = (action.suggested_change or "").lower()
                title_lower = (action.title or "").lower()
                
                # Skip actions with analysis-tool language
                if any(phrase in suggested_change_lower or phrase in title_lower 
                       for phrase in forbidden_phrases):
                    logger.info(f"Filtered out analysis-tool next_better_action: {action.title}")
                    continue
                
                # Prioritize actions with SaaS pricing preferred phrases
                if any(phrase in suggested_change_lower for phrase in preferred_phrases):
                    filtered_actions.insert(0, action)  # Add to front
                else:
                    filtered_actions.append(action)
            
            # Ensure we still have at least 3 actions
            if len(filtered_actions) < 3:
                logger.warning(f"After SaaS pricing filtering, only {len(filtered_actions)} actions remain. Keeping original actions.")
                next_better_actions = next_better_actions  # Keep original if too few remain
            else:
                next_better_actions = filtered_actions
                # Re-assign priority_rank sequentially
                for idx, action in enumerate(next_better_actions, 1):
                    action.priority_rank = idx
        
        # Filter service/clinic-inappropriate actions
        if is_service_clinic:
            filtered_actions = []
            forbidden_phrases = [
                "know exactly why users don't decide",
                "decision diagnosis",
                "analysis tool",
                "conversion diagnosis",
                "see the one reason",
                "free trial",
                "sign up",
                "get started"
            ]
            
            preferred_phrases = [
                "reassurance",
                "risk reduction",
                "next steps",
                "what to expect",
                "explanation",
                "trust",
                "guarantee",
                "safety"
            ]
            
            for action in next_better_actions:
                suggested_change_lower = (action.suggested_change or "").lower()
                title_lower = (action.title or "").lower()
                
                # Skip actions with analytical/SaaS language
                if any(phrase in suggested_change_lower or phrase in title_lower 
                       for phrase in forbidden_phrases):
                    logger.info(f"Filtered out analytical next_better_action from service/clinic: {action.title}")
                    continue
                
                # Also check if it's an "Outcome Unclear" related action
                if "outcome unclear" in title_lower or "outcome unclear" in suggested_change_lower:
                    logger.info(f"Filtered out 'Outcome Unclear' action from service/clinic: {action.title}")
                    continue
                
                # Prioritize actions with preferred service/clinic phrases
                if any(phrase in suggested_change_lower for phrase in preferred_phrases):
                    filtered_actions.insert(0, action)  # Add to front
                else:
                    filtered_actions.append(action)
            
            # Ensure we still have at least 3 actions
            if len(filtered_actions) < 3:
                logger.warning(f"After service/clinic filtering, only {len(filtered_actions)} actions remain. Keeping original actions.")
                next_better_actions = next_better_actions  # Keep original if too few remain
            else:
                next_better_actions = filtered_actions
                # Re-assign priority_rank sequentially
                for idx, action in enumerate(next_better_actions, 1):
                    action.priority_rank = idx
        
        # Filter marketplace-inappropriate actions
        if is_marketplace:
            filtered_actions = []
            forbidden_phrases = [
                "know exactly why users don't decide",
                "decision diagnosis",
                "analysis tool",
                "conversion diagnosis",
                "see the one reason",
                "free trial",
                "sign up",
                "get started",
                "learn more about",
                "analyze",
                "diagnosis"
            ]
            
            for action in next_better_actions:
                suggested_change_lower = (action.suggested_change or "").lower()
                title_lower = (action.title or "").lower()
                
                # Skip actions with SaaS/analytical language
                if any(phrase in suggested_change_lower or phrase in title_lower 
                       for phrase in forbidden_phrases):
                    logger.info(f"Filtered out SaaS-style next_better_action: {action.title}")
                    continue
                
                # Also check if it's an "Outcome Unclear" related action
                if "outcome unclear" in title_lower or "outcome unclear" in suggested_change_lower:
                    logger.info(f"Filtered out 'Outcome Unclear' action: {action.title}")
                    continue
                
                filtered_actions.append(action)
            
            # Ensure we still have at least 3 actions
            if len(filtered_actions) < 3:
                logger.warning(f"After marketplace filtering, only {len(filtered_actions)} actions remain. Keeping original actions.")
                next_better_actions = next_better_actions  # Keep original if too few remain
            else:
                next_better_actions = filtered_actions
                # Re-assign priority_rank sequentially
                for idx, action in enumerate(next_better_actions, 1):
                    action.priority_rank = idx
        
        result.next_better_actions = next_better_actions
        logger.info(f"Next better actions built: {len(next_better_actions)} actions (marketplace={is_marketplace})")
    except Exception as e:
        logger.error(f"Failed to build next_better_actions: {e}", exc_info=True)
        # This field must always have at least 3 actions - create defaults if build failed
        result.next_better_actions = build_next_better_actions({})  # Will create default actions

    # --- Executive decision layer (safe defaults) ---
    # Extract data from outcome_analysis and metadata
    decision_summary = outcome_analysis.dict() if 'outcome_analysis' in locals() else {}
    failure_breakdown = normalized.get("metadata", {}).get("outcome_analysis", {}) if 'normalized' in locals() else {}
    
    # Get decision stage from parsed JSON - validate and set default only if invalid/missing
    decision_stage = None
    
    # Try to get from top-level first
    if "decision_stage" in normalized:
        decision_stage = normalized.get("decision_stage")
    # Try from metadata
    elif normalized.get("metadata", {}).get("decision_stage_assessment", {}).get("stage"):
        decision_stage = normalized.get("metadata", {}).get("decision_stage_assessment", {}).get("stage")
    # Try from executive_decision_summary if it exists
    elif normalized.get("executive_decision_summary", {}).get("decision_stage"):
        decision_stage = normalized.get("executive_decision_summary", {}).get("decision_stage")
    
    # Validate decision_stage - must be one of the four valid values
    valid_stages = {"awareness", "sense_making", "evaluation", "commitment"}
    
    if decision_stage not in valid_stages:
        logger.warning(
            f"[CF ENGINE] Invalid or missing decision_stage='{decision_stage}', "
            f"defaulting to 'sense_making'"
        )
        decision_stage = "sense_making"
    
    # Read what_to_fix_first from parsed JSON if available
    parsed_what_to_fix_first_final = parsed_what_to_fix_first if 'parsed_what_to_fix_first' in locals() and parsed_what_to_fix_first else None
    if not parsed_what_to_fix_first_final and decision_summary:
        parsed_what_to_fix_first_final = decision_summary.get("priority_fix")
    
    # Read recommendations from parsed JSON if available
    parsed_recommendations_final = parsed_recommendations if 'parsed_recommendations' in locals() and parsed_recommendations else None
    if not parsed_recommendations_final:
        parsed_recommendations_final = normalized.get("ai_recommendations")
    
    # Only use fallback values if we truly don't have data from the model
    # This should only happen in error cases, not normal operation
    use_fallback = not decision_summary and not parsed_primary_outcome
    
    if use_fallback:
        logger.warning("[CF ENGINE] Using fallback static response due to missing model data")
    
    executive_decision_summary = {
        "primary_outcome": (
            decision_summary.get("primary_outcome") if decision_summary 
            else (parsed_primary_outcome if 'parsed_primary_outcome' in locals() and parsed_primary_outcome 
                  else ("No clear decision" if use_fallback else None))
        ),
        "confidence": (
            float(decision_summary.get("primary_confidence", 0.0)) * 100.0 if decision_summary 
            else (parsed_confidence * 100.0 if 'parsed_confidence' in locals() and parsed_confidence is not None 
                  else (0.0 if use_fallback else None))
        ),
        "decision_stage": decision_stage,
        "summary": (
            decision_summary.get("psychological_explanation") if decision_summary 
            else ("The input didn't contain enough decision-related information." if use_fallback else None)
        ),
    }
    
    decision_failure_breakdown = {
        "primary_outcome": (
            decision_summary.get("primary_outcome") if decision_summary 
            else (parsed_primary_outcome if 'parsed_primary_outcome' in locals() and parsed_primary_outcome 
                  else ("No specific failure detected" if use_fallback else None))
        ),
        "confidence": (
            float(decision_summary.get("primary_confidence", 0.0)) * 100.0 if decision_summary 
            else (parsed_confidence * 100.0 if 'parsed_confidence' in locals() and parsed_confidence is not None 
                  else (0.0 if use_fallback else None))
        ),
        "reasons": (
            [parsed_what_to_fix_first_final] if parsed_what_to_fix_first_final 
            else ([decision_summary.get("priority_fix")] if decision_summary and decision_summary.get("priority_fix") 
                  else ([] if not use_fallback else ["Analysis incomplete - insufficient data from model"]))
        ),
    }
    
    # Set the new fields on result
    result.executive_decision_summary = executive_decision_summary
    result.decision_failure_breakdown = decision_failure_breakdown

    return result

