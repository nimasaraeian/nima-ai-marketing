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

You are **Cognitive Friction Vision Engine**, an expert behavioral UX + psychology analyst.

You receive:
- A landing page screenshot (image of the full page or hero section).
- Optional raw text of the page (headline, subheadline, body, CTAs).

Your job:
- Reconstruct the structure of the page from the image.
- Detect which exact visual and textual elements create cognitive friction.
- Explain *where* the problem is, *why* it is a problem psychologically, and *how* to fix it.
- Always connect issues to psychological pillars: clarity, trust, emotion, motivation, overload, and ambiguity.

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


class VisualTrustAnalysis(BaseModel):
    """Structured visual trust output."""

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
        description="Structured visual trust evaluation for accompanying imagery.",
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

    return result

