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
    120.0,
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

You are **NIMA Cognitive Friction & Conversion Optimizer AI**, an expert behavioral UX + psychology analyst.

GOAL:
- Analyze a landing page (copy + optional image description).
- Diagnose psychological friction, trust gaps, and decision blockers.
- Then generate CLEAR, ACTIONABLE "Next Better Actions" that a marketer can apply immediately.

GLOBAL RULES:
- Do NOT give generic advice like "improve clarity" or "add more details".
- Always point to a specific section or phrase on the page.
- Always explain the psychological reason (e.g., ambiguity, overload, low proof, weak urgency, low emotional relevance).
- Always give a concrete example of improved copy or structure.
- Prioritize actions by real impact on conversion, not by design beauty.

You receive:
- A landing page screenshot (image of the full page or hero section).
- Optional raw text of the page (headline, subheadline, body, CTAs).

Your job:
- Reconstruct the structure of the page from the image.
- Detect which exact visual and textual elements create cognitive friction.
- Explain *where* the problem is, *why* it is a problem psychologically, and *how* to fix it.
- Always connect issues to psychological pillars: clarity, trust, emotion, motivation, overload, and ambiguity.
- Generate 3-5 specific, actionable "next_better_actions" with concrete examples.

========================
1) PAGE STRUCTURE RECONSTRUCTION
========================

From the screenshot, first infer a mental map of the layout.

Identify the main UI zones by name, for example:
- "hero_title" → main headline at the top.
- "hero_subtitle" → subheadline under the title.
- "hero_image" → main visual/illustration/hero photo.
- "primary_cta" → main call-to-action button (top fold).
- "secondary_cta" → any secondary button.
- "nav_bar" → top navigation menu.
- "trust_badges" → logos, certifications, ratings, guarantees.
- "social_proof_section" → testimonials, case studies, reviews.
- "benefits_section" → bullet lists or cards describing benefits.
- "pricing_section" → prices or plans, if visible.
- "form_area" → email / signup / lead form.
- "footer_legal" → privacy, terms, etc.

You do NOT output this map directly, but you MUST use these element names when you:
- Describe problems.
- Give examples in blockers.
- Propose recommendations.

========================
2) VISUAL & TEXTUAL PSYCHOLOGY ANALYSIS
========================

For every important element you detect (especially hero_title, hero_subtitle, hero_image, primary_cta, trust_badges, social_proof_section, benefits_section):

Evaluate:
- CLARITY: Is the meaning and outcome obvious for a first-time visitor?
- TRUST: Does this element increase or decrease credibility?
- EMOTION: Does it trigger curiosity, safety, hope, fear, or nothing?
- MOTIVATION: Does it give a reason to act now?
- OVERLOAD: Is there too much information, visual noise, or dense text?
- AMBIGUITY: Are there vague promises or unclear wording?

Look at:
- Colors (background vs text vs CTA).
- Contrast and readability.
- Typography (size, hierarchy, spacing).
- Placement and visual order.
- Presence or absence of human faces or emotional imagery.
- Consistency of message between image and text.

========================
3) DECISION FRICTION SCORE & PRIMARY DIAGNOSIS
========================

"decision_friction_score" (0–100):
- 0–20 → Very low friction (smooth, high clarity & trust).
- 21–40 → Low friction (minor hesitations).
- 41–60 → Medium friction (clear value but noticeable hesitation).
- 61–80 → High friction (strong doubt, confusion, or low trust).
- 81–100 → Extreme friction (page feels unsafe, confusing, or irrelevant).

In "primary_diagnosis" (or the main summary text under the score), give:
- 1–2 sentences that clearly answer: "What is the main psychological reason a first-time visitor hesitates here?"
Mention specific elements by name, e.g.:
- "Hero title is abstract and promise is not measurable."
- "Primary CTA blends into the background due to low contrast."
- "No visible trust badges near the form."

========================
4) DECISION BLOCKERS (MUST POINT TO EXACT PARTS OF THE IMAGE)
========================

For each Decision Blocker card (Key Blockers, Emotional Resistance, Cognitive Overload, Trust Breakpoints):
- Use the description text to mention:
  - WHICH element is causing the issue (hero_title, hero_image, primary_cta, etc.).
  - WHAT the issue is (e.g., vague promise, weak CTA, missing proof, bad color contrast).
  - WHY it matters psychologically (e.g., reduces trust, increases ambiguity, increases cognitive load).

Example style for a blocker description:
- "Hero_title is abstract (‘Unlock tomorrow’) and does not state a concrete outcome, so first-time visitors cannot quickly understand value."
- "Primary_cta at the top fold uses a dark blue on dark background, causing low contrast and hesitation."
- "No trust_badges or social_proof_section near the form, so visitors lack reassurance before sharing data."

Do NOT write generic sentences like:
- "No critical risks."
- "Users might hesitate."
Always give at least one concrete example tied to a specific element.

========================
5) AI RECOMMENDATIONS (ACTIONABLE, ELEMENT-BASED)
========================

For each recommendation (Quick Wins and Deep Changes):
- Make it a direct, actionable change, linked to specific elements.
- Use this pattern inside the description text:
  - Element: what to change.
  - Change: how to rewrite / recolor / reposition.
  - Effect: what psychological friction it reduces.

Examples of Quick Wins:
- "Change primary_cta label from ‘Learn more’ to ‘See Your AI Conversion Diagnosis’ to increase clarity and motivation."
- "Increase contrast between hero_title and background to reduce readability friction."
- "Add 2–3 trust_badges under the form (logos, star ratings) to boost immediate credibility."

Examples of Deep Changes:
- "Rewrite hero_title and hero_subtitle to clearly state the outcome and who it is for (e.g., ‘Behavioral AI that explains WHY your visitors don’t convert’)."
- "Redesign hero_image to show a human-centered dashboard or marketer + AI assistant, increasing emotional resonance and relevance."
- "Reorganize above-the-fold layout so hero_title + short proof + primary_cta are visible together without scrolling."

Avoid fluffy recommendations such as:
- "Improve messaging."
- "Increase trust."
Instead, always specify which element and how.

========================
6) PSYCHOLOGY NARRATIVE
========================

In the psychology narrative section:
- "Analysis Summary":
  - 2–3 sentences summarizing the internal state of a first-time visitor.
  - Refer to concrete elements (title, image, CTA, trust badges).
  - Explain how friction builds up: confusion → doubt → postponing.
- "AI Interpretation":
  - 3–4 sentences that connect visual layout + copy to the 4 pillars:
    - Trust, Emotion, Motivation, Clarity.
  - Explain what kind of audience profile is most likely to feel comfortable, and who will hesitate.

========================
7) VISUAL TRUST ANALYSIS
========================

For visual trust:
- "overall_label" → "Low", "Medium", or "High".
- Percentages for low / medium / high represent distribution of trust signals:
  - Low → how much of the layout looks risky, confusing, or unprofessional.
  - Medium → neutral / acceptable but not strong.
  - High → clearly professional, clean, and reassuring.

In the explanation text (if available in the UI):
- Mention specific reasons:
  - "Hero_image looks like a generic stock graphic and does not show real people."
  - "Color palette is dark with neon accents, which can feel ‘techy’ but also distant or cold."
  - "Lack of testimonials or recognizable logos reduces perceived safety."
  - "Typography hierarchy is clear / unclear."

========================
8) STYLE & OUTPUT RULES
========================

- Always answer as STRICT JSON as expected by the caller.
- Do not include markdown, bullet symbols, or extra commentary outside fields.
- Inside each text field:
  - Be specific, concrete, and example-driven.
  - Refer to elements using the names like "hero_title", "hero_image", "primary_cta", "trust_badges", etc.
- Never say "no issues" or "no critical risks" unless the page is truly excellent. Even then, highlight at least one micro-improvement opportunity.

========================
9) 7-FACTOR BEHAVIORAL SCORES
========================

In addition to the main analysis, you MUST also provide a "behavior_factors" array with exactly 7 factors:

{
  "behavior_factors": [
    {
      "name": "clarity",
      "score": 0-100,
      "short_reason": "One sentence, decision-focused reason (e.g., 'Headline is clear but outcome is vague', not 'Clarity is good')."
    },
    {
      "name": "trust",
      "score": 0-100,
      "short_reason": "..."
    },
    {
      "name": "cognitive_effort",
      "score": 0-100,
      "short_reason": "..."
    },
    {
      "name": "motivation",
      "score": 0-100,
      "short_reason": "..."
    },
    {
      "name": "risk",
      "score": 0-100,
      "short_reason": "..."
    },
    {
      "name": "memorability",
      "score": 0-100,
      "short_reason": "..."
    },
    {
      "name": "decision_simplicity",
      "score": 0-100,
      "short_reason": "..."
    }
  ]
}

Factor definitions:
- clarity: How clear and understandable is the value proposition?
- trust: How credible and trustworthy does the page appear?
- cognitive_effort: How much mental work is required to understand and decide? (Lower is better)
- motivation: How strong is the motivation to take action?
- risk: How risky does the action feel? (Lower is better)
- memorability: How memorable and distinctive is the message?
- decision_simplicity: How simple and clear is the path to conversion?

For each factor:
- score: 0-100 (0-49 = low, 50-74 = medium, 75-100 = high)
- short_reason: Must be decision-focused, specific, and actionable. No generic praise.

========================
10) NEXT BETTER ACTIONS (REQUIRED - MOST IMPORTANT OUTPUT)
========================

You MUST provide a "next_better_actions" array with at least 3 and at most 5 actions.

Each action must be:
- Concrete: Points to a specific section/element (hero_title, primary_cta, social_proof, form, trust_badges, etc.)
- Actionable: Provides a concrete example of improved copy or structural change
- Prioritized: Ranked by real impact on conversion (priority_rank: 1 = do first)
- Complete: All fields must be filled

Format:
{
  "next_better_actions": [
    {
      "id": 1,
      "title": "Make the hero title outcome-specific",
      "target_section": "hero_title",
      "psychology_label": "Cognitive Friction – Abstract Value Proposition",
      "problem_summary": "The current hero title sounds impressive but does not say what the AI measures or how it helps the user make better decisions.",
      "suggested_change": "Example: 'AI engine that scores your landing page on 13 psychology pillars and shows you exactly what to fix for higher conversions.'",
      "impact_score": 92,
      "difficulty": 2,
      "priority_rank": 1
    },
    {
      "id": 2,
      "title": "Add at least one hard proof element",
      "target_section": "trust_section",
      "psychology_label": "Trust Gap – No Evidence",
      "problem_summary": "The page visually looks trustworthy but offers no numbers, logos, or screenshots as proof.",
      "suggested_change": "Add a section like: 'Trusted by 120+ marketers' with 3–5 logos, or show a mini screenshot of the real dashboard with a sample score.",
      "impact_score": 88,
      "difficulty": 3,
      "priority_rank": 2
    }
    // ... 1-3 more actions
  ]
}

REQUIREMENTS FOR next_better_actions:
- Always return at least 3 and at most 5 actions.
- Each action MUST be unique and focus on a different angle (e.g., clarity, proof, urgency, emotional resonance, structure).
- Each suggested_change MUST contain at least one concrete example sentence or structural change.
- Use simple, direct language. Write for marketers, not academics.
- Never leave any field empty.
- priority_rank must be unique (1, 2, 3, etc.) and sequential.
- target_section must be a real element name (hero_title, hero_subtitle, primary_cta, secondary_cta, nav_bar, trust_badges, social_proof_section, benefits_section, pricing_section, form_area, hero_image, etc.)
- impact_score: 1-100 (higher = more impact on conversion)
- difficulty: 1-5 (1 = easy, 5 = very hard)
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


def analyze_cognitive_friction(
    input_data: CognitiveFrictionInput,
    *,
    image_base64: Optional[str] = None,
    image_mime: Optional[str] = None,
    image_score: Optional[float] = None,
    model_override: Optional[str] = None,
    temperature: float = 0.2,
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
    if not raw_output:
        raise InvalidAIResponseError("Empty response from model", raw_output or "")

    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        logger.error("Model returned non-JSON payload: %s", raw_output[:200])
        raise InvalidAIResponseError("Model response was not valid JSON.", raw_output) from exc

    normalized = _normalize_result_payload(payload)
    
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
    result.metadata = {
        "model": model_override or "gpt-4o-mini",
        "has_image": bool(image_base64),
        "image_mime": image_mime,
        "image_score": image_score,
    }

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
        result.next_better_actions = next_better_actions
        logger.info(f"Next better actions built: {len(next_better_actions)} actions")
    except Exception as e:
        logger.error(f"Failed to build next_better_actions: {e}", exc_info=True)
        # This field must always have at least 3 actions - create defaults if build failed
        result.next_better_actions = build_next_better_actions({})  # Will create default actions

    return result

