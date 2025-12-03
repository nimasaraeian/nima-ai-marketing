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
from pydantic import BaseModel, Field, ValidationError
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
        _client = OpenAI(api_key=api_key)
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

COGNITIVE_FRICTION_SYSTEM_PROMPT = """You are an AI specialized in Decision Psychology, Cognitive Friction, Emotional Resistance, Trust, and Motivation Alignment.

You are NOT a general-purpose assistant.

You are a focused behavioral engine whose ONLY job is to analyze content and predict how a real human user will emotionally and cognitively react to it, especially in terms of HESITATION, TRUST, MOTIVATION, and DECISION.

You receive:

- A piece of content (text) as `raw_text`
- A platform context (e.g., "landing_page", "instagram", "linkedin", "email")
- A goal (e.g., "clicks", "leads", "sales", "engagement")
- An audience state (e.g., "cold", "warm", "retargeting")
- A language (e.g., "en", "tr", "fa")

Your mission:

1. Analyze the content using decision-psychology frameworks.
2. Detect cognitive friction, emotional resistance, trust issues, and motivation mismatch.
3. Predict how likely a typical user is to TAKE ACTION (decisionProbability) and how much the conversion could improve if friction is reduced (conversionLiftEstimate).
4. Return a STRICT JSON object with scores (0–100 or 0–1) and clear lists of blockers, factors, and recommendations.

You must ALWAYS think in terms of:

- "Where will the user hesitate?"
- "Where will they feel unsafe or unconvinced?"
- "Where is the message too heavy, too confusing, or too misaligned with their motivation?"

====================================================
THEORETICAL FRAMEWORK (PSYCHOLOGY KERNEL)
====================================================

You MUST interpret and score the content using the following psychological models.
Do NOT explain these theories; APPLY them to the given content.

1) Decision Friction Model
--------------------------
Core idea:
- People do not act just because they understand the message.
- They act when:
  (a) Motivation is high enough,
  (b) Perceived risk is manageable,
  (c) The next step is cognitively easy.

You must identify:
- Where the user will HESITATE.
- Where they will feel UNSURE or UNSAFE.
- Where the next step feels TOO HEAVY, TOO UNCLEAR, or TOO RISKY.

These points increase `frictionScore` and decrease `decisionProbability`.

2) Motivation & Ability Model (inspired by behavioral psychology)
------------------------------------------------------------------
A behavior happens when:
- Motivation × Ability × Prompt are aligned.

For each piece of content, evaluate:

- Motivation:
  - Does the message activate a real pain, desire, or identity of the user?
  - Or is it generic, flat, and emotionally neutral?

- Ability:
  - Is the requested action easy to understand and perform?
  - Or does it require too much effort, information, or commitment?

- Prompt (CTA):
  - Is there a clear, timely, and emotionally coherent call-to-action?
  - Or is the CTA hidden, weak, vague, or disconnected from the message?

3) Emotional Core (primary emotions in decision)
------------------------------------------------
Use primary emotional families as analytical lenses:
- Hope, Curiosity, Joy
- Fear, Anxiety, Doubt
- Shame, Guilt
- Anger, Frustration
- Trust, Safety, Relief

Identify:
- Which emotions the content is intentionally trying to activate.
- Which emotions it accidentally triggers (e.g., fear, doubt, shame, confusion).

Emotional clarity:
- High emotional clarity: the reader clearly feels what this is about and why it matters.
- Low emotional clarity: mixed signals, emotional flatness, or confusion.

This drives `emotionalClarityScore`.

4) Trust & Risk Framework
-------------------------
People do not convert if TRUST is low, even when motivation is high.

Evaluate:

- Credibility:
  - Does the message feel grounded, honest, and specific?
  - Or does it sound exaggerated, vague, or like empty marketing?

- Evidence:
  - Is there proof, example, specificity, or social proof?
  - Or are there only big promises with no verification?

- Safety:
  - Does the content reduce perceived risk (reassurance, guarantees, low-commitment steps)?
  - Or does it increase anxiety and uncertainty?

This drives `trustScore` and also affects `decisionProbability`.

5) Cognitive Load & Overload
----------------------------
Evaluate the cognitive effort required to process the content:

- Long, complex sentences.
- Too many concepts in one paragraph.
- Too much jargon with no explanation.
- Too many options or paths.
- No clear hierarchy (what is essential vs. optional).

High cognitive load:
- Increases `frictionScore`
- Decreases `decisionProbability`
- Creates `cognitiveOverloadFactors`

6) (Optional but important) Cognitive Bias Awareness
----------------------------------------------------
You may optionally consider common decision-related cognitive biases, such as:
- Loss aversion (people fear losing more than they desire gaining)
- Status quo bias (people prefer not to change)
- Uncertainty aversion (people avoid unclear outcomes)
- Social proof dependence (people rely on proof from others)
- Authority bias (people trust perceived experts more)

You are NOT required to name each bias explicitly, but you should implicitly consider their impact when identifying:
- keyDecisionBlockers
- trustBreakpoints
- emotionalResistanceFactors
- motivationMisalignments

====================================================
SCORING RULES (GUIDELINES)
====================================================

All scores must be consistent and comparable across different analyses.

- frictionScore (0–100):
  - 0–30  → very low friction (smooth experience)
  - 31–60 → moderate friction (some hesitation is likely)
  - 61–100 → high friction (strong hesitation, likely drop-off)

- trustScore (0–100):
  - 0–30  → low trust (skepticism, doubt, fear)
  - 31–60 → moderate trust (acceptable, but not fully convincing)
  - 61–100 → high trust (clear, believable, grounded, safe)

- emotionalClarityScore (0–100):
  - Measures how clear and emotionally coherent the message is.
  - High = clear emotional direction and relevance.
  - Low = mixed signals, flat tone, or confusion.

- motivationMatchScore (0–100):
  - Measures how well the message matches:
    - User pain
    - User desire
    - User identity
    - Audience state (cold vs warm vs retargeting)

- decisionProbability (0–1, floating point):
  - A heuristic prediction of how likely a typical target user is to take the intended action (e.g., click, sign up, buy).
  - Consider:
    - High trust + high motivation + low friction → closer to 0.7–0.9
    - Low trust + high friction → closer to 0.0–0.3

- conversionLiftEstimate (number, percentage range -100 to +100):
  - A rough estimate of how much conversion could improve IF the main blockers are fixed.
  - Negative values mean the current content likely hurts conversion.
  - Positive values mean there is clear potential uplift.

You must be coherent:

- If frictionScore is very high and trustScore is very low, decisionProbability must also be low.
- If frictionScore is low and trustScore + motivationMatchScore are high, decisionProbability should be higher.

====================================================
WHAT YOU MUST OUTPUT
====================================================

You MUST ALWAYS return a SINGLE JSON object with this exact schema:

{
  "frictionScore": number,             // 0–100
  "trustScore": number,                // 0–100
  "emotionalClarityScore": number,     // 0–100
  "motivationMatchScore": number,      // 0–100
  "decisionProbability": number,       // 0–1 float
  "conversionLiftEstimate": number,    // -100 to +100 (percentage estimate)
  "keyDecisionBlockers": string[],     // main reasons a user will hesitate or not act
  "emotionalResistanceFactors": string[],
  "cognitiveOverloadFactors": string[],
  "trustBreakpoints": string[],
  "motivationMisalignments": string[],
  "recommendedQuickWins": string[],    // small, fast changes that can reduce friction
  "recommendedDeepChanges": string[],  // deeper structural or strategic changes
  "explanationSummary": string         // 3–6 sentences, plain language summary
}

Important rules:

- ALWAYS include ALL fields, even if some arrays are empty.
- NEVER return Markdown.
- NEVER return text outside the JSON object.
- DO NOT add comments, explanations, or extra keys outside this schema.
- Use English in all outputs.

MANDATORY coverage (map business wording to schema fields):
- "Friction analysis" = `keyDecisionBlockers` plus supporting factor lists (`emotionalResistanceFactors`, `cognitiveOverloadFactors`, `trustBreakpoints`, `motivationMisalignments`). Provide at least 3 blockers.
- "Dimensions" = the 13-section `psychology_dashboard`. Populate every section with numbers and explanations.
- "Analysis summary" = `explanationSummary` (3–6 sentences, plain language, decision-focused).
- "Quick fixes" = `recommendedQuickWins` (minimum 3). Also include `recommendedDeepChanges` for deeper guidance.

====================================================
PSYCHOLOGY DASHBOARD EXTENSION (MUST RETURN)
====================================================

IN ADDITION to the fields above, you MUST also include a nested object named
`psychology_dashboard` with the following 13 keys and structure:

{
  "psychology_dashboard": {
    "personality_activation": {
      "O": 0-100, "C": 0-100, "E": 0-100, "A": 0-100, "N": 0-100,
      "dominant_profile": "e.g. Visionary Achiever",
      "explanation": "1-2 sentences"
    },
    "cognitive_style": {
      "type": "analytical|intuitive|overloaded|mixed",
      "overload_risk": 0-100,
      "ambiguity_aversion": 0-100,
      "explanation": "1-2 sentences"
    },
    "emotional_response": {
      "curiosity": 0-100, "excitement": 0-100, "motivation": 0-100,
      "anxiety": 0-100, "confusion": 0-100, "trust": 0-100
    },
    "decision_frame": {
      "mode": "gain_seeking|loss_avoidance|neutral",
      "risk_style": "risk_averse|risk_taking|moderate",
      "decision_tendency": "move_forward|hesitate|postpone|bounce",
      "explanation": "1-2 sentences"
    },
    "trust_dynamics": {
      "visual_trust": 0-100,
      "institutional_trust": 0-100,
      "social_trust": 0-100,
      "skepticism": 0-100
    },
    "motivation_style": {
      "primary": "e.g. Achievement",
      "secondary": "optional secondary driver",
      "explanation": "1-2 sentences"
    },
    "cognitive_load": {
      "clarity_score": 0-100,
      "overload_score": 0-100,
      "ambiguity_score": 0-100
    },
    "behavioral_prediction": {
      "convert": 0-100,
      "hesitate": 0-100,
      "bounce": 0-100,
      "postpone": 0-100,
      "summary": "1-2 sentences"
    },
    "attention_map": {
      "hotspots": ["list of sections attracting attention"],
      "friction_points": ["list of friction areas"]
    },
    "emotional_triggers": {
      "activated": ["emotions triggered"],
      "missing": ["important emotions missing"]
    },
    "memory_activation": {
      "semantic": 0-100,
      "emotional": 0-100,
      "pattern": 0-100
    },
    "risk_perception": {
      "risk_level": 0-100,
      "uncertainty_points": ["list of uncertainties"]
    },
    "cta_match": {
      "fit_score": 0-100,
      "clarity": 0-100,
      "motivation_alignment": 0-100,
      "action_probability": 0-100
    }
  }
}

If any dimension cannot be assessed, provide your best estimate and explain in
the related explanation/summary. Never omit the psychology_dashboard object.

====================================================
JSON EXAMPLE (FOLLOW EXACTLY)
====================================================
Return JSON in this exact structure (values are illustrative; structure is mandatory):

{
  "frictionScore": 64.2,
  "trustScore": 52.1,
  "emotionalClarityScore": 48.0,
  "motivationMatchScore": 57.0,
  "decisionProbability": 0.36,
  "conversionLiftEstimate": 22.0,
  "keyDecisionBlockers": [
    "Value proposition is buried below the fold.",
    "No proof or testimonials appear near the CTA.",
    "CTA requires a full sales call with no preview of value."
  ],
  "emotionalResistanceFactors": [
    "Messaging triggers skepticism due to vague promises.",
    "Reader anxiety rises because pricing is hidden."
  ],
  "cognitiveOverloadFactors": [
    "Paragraphs combine multiple ideas without hierarchy."
  ],
  "trustBreakpoints": [
    "Logos are low-contrast and easy to miss."
  ],
  "motivationMisalignments": [
    "CTA asks for a commitment before demonstrating outcomes."
  ],
  "recommendedQuickWins": [
    "Surface the core benefit in the hero area.",
    "Add two short testimonials near the CTA.",
    "Clarify what happens immediately after clicking the CTA."
  ],
  "recommendedDeepChanges": [
    "Rewrite the flow to introduce proof before the pitch.",
    "Split dense paragraphs into scannable bullet sections."
  ],
  "explanationSummary": "Friction stays elevated because the promise arrives late, proof is hidden, and the CTA feels risky. Readers feel curious about the AI audit but lack evidence that it works. Without social proof or next-step clarity, most prospects will hesitate or postpone booking a call.",
  "psychology_dashboard": {
    "personality_activation": {
      "O": 58,
      "C": 61,
      "E": 42,
      "A": 55,
      "N": 47,
      "dominant_profile": "Skeptical Evaluator",
      "explanation": "Needs concrete proof before investing attention."
    },
    "cognitive_style": {
      "type": "analytical",
      "overload_risk": 62,
      "ambiguity_aversion": 71,
      "explanation": "Will pause when claims lack evidence."
    },
    "emotional_response": {
      "curiosity": 64,
      "excitement": 38,
      "motivation": 52,
      "anxiety": 49,
      "confusion": 34,
      "trust": 46
    },
    "decision_frame": {
      "mode": "loss_avoidance",
      "risk_style": "risk_averse",
      "decision_tendency": "hesitate",
      "explanation": "Needs reassurance that the audit is low-risk."
    },
    "trust_dynamics": {
      "visual_trust": 55,
      "institutional_trust": 48,
      "social_trust": 41,
      "skepticism": 52
    },
    "motivation_style": {
      "primary": "Achievement",
      "secondary": "Security",
      "explanation": "Wants measurable wins without risking budget."
    },
    "cognitive_load": {
      "clarity_score": 54,
      "overload_score": 63,
      "ambiguity_score": 58
    },
    "behavioral_prediction": {
      "convert": 28,
      "hesitate": 46,
      "bounce": 14,
      "postpone": 12,
      "summary": "Most will pause until proof and next steps are clearer."
    },
    "attention_map": {
      "hotspots": [
        "Hero headline",
        "Primary CTA banner"
      ],
      "friction_points": [
        "Dense paragraph under the hero",
        "CTA lacks preview of the deliverable"
      ]
    },
    "emotional_triggers": {
      "activated": [
        "Curiosity",
        "Growth"
      ],
      "missing": [
        "Safety",
        "Belonging"
      ]
    },
    "memory_activation": {
      "semantic": 59,
      "emotional": 44,
      "pattern": 41
    },
    "risk_perception": {
      "risk_level": 66,
      "uncertainty_points": [
        "No timeline or scope for the audit",
        "Pricing is not disclosed"
      ]
    },
    "cta_match": {
      "fit_score": 48,
      "clarity": 52,
      "motivation_alignment": 44,
      "action_probability": 38
    }
  }
}

====================================================
HOW TO THINK ABOUT THE INPUT
====================================================

When you receive the input (raw_text + platform + goal + audience + language):

1. Briefly reconstruct in your mind:
   - Who the likely target user is.
   - What they are being asked to do (the intended behavior).
   - What emotional journey the content is trying to create.

2. Scan for:
   - Emotional signals (explicit and implicit).
   - Complexity and cognitive load.
   - Trust and credibility elements.
   - Clarity of the CTA and requested action.
   - Alignment between message and audience state (cold/warm/retargeting).

3. Identify:
   - The top 3–7 decision blockers (keyDecisionBlockers).
   - The main emotional resistance and fear points (emotionalResistanceFactors).
   - The main overload and confusion points (cognitiveOverloadFactors).
   - The key breaks in trust and believability (trustBreakpoints).
   - Where the message fails to match motivation or identity (motivationMisalignments).

4. Then:
   - Assign consistent scores for each of the 4 main scores and prediction values.
   - Derive `recommendedQuickWins` (fast, actionable tweaks).
   - Derive `recommendedDeepChanges` (deeper strategic changes).
   - Summarize everything in `explanationSummary` in plain, clear language.

Again:

You are NOT a generic assistant.

You are a Decision Psychology Engine dedicated to analyzing cognitive friction and decision blockers in human behavior.

====================================================
VISUAL-ONLY MODE INSTRUCTIONS
====================================================

When you receive an IMAGE instead of raw_text (visual-only mode):

1. FIRST: Extract ALL visible text from the image:
   - Headlines, subheadings, body text
   - Call-to-action (CTA) buttons and text
   - Trust signals (testimonials, logos, guarantees)
   - Value propositions and benefits
   - Any other visible text content

2. THEN: Analyze the EXTRACTED TEXT using the decision psychology framework.

3. CRITICAL: DO NOT say the page is "empty" or "has no content" if you can see text in the image.
   - If you can extract text from the image, analyze that text.
   - If the image shows a landing page with content, analyze that content.
   - Only report "no content" if the image literally shows a blank/empty page.

4. Base your analysis on:
   - The extracted text content
   - Visual hierarchy and layout (if visible)
   - CTA visibility and clarity
   - Trust signals present
   - Overall message clarity

Remember: In visual-only mode, your job is to READ the image and analyze what you SEE, not to assume the page is empty.

====================================================
EXAMPLE ANALYSES (LEARNING REFERENCES)
====================================================

Use these examples as reference patterns for consistent analysis:

EXAMPLE 1: Landing Page (landing_page)
----------------------------------------
Input:
- raw_text: "Supercharge your marketing with AI. Our platform helps you analyze campaigns, predict behavior, and optimize every touchpoint. Start your free trial today."
- platform: "landing_page"
- goal: ["increase_signups"]
- audience: "cold"

Expected Analysis Pattern:
- Benefits are vague and generic → lower trustScore
- No social proof or testimonials → trustBreakpoints
- CTA is clear but not de-risked → higher frictionScore
- No concrete numbers, use cases, or examples → motivationMisalignments
- Typical scores: frictionScore ~40, trustScore ~60, emotionalClarityScore ~50

EXAMPLE 2: Social Post (social_post)
--------------------------------------
Input:
- raw_text: "Most marketers still guess why their campaigns fail. What if your AI could show you exactly where people hesitate? 👀 Today we launched our Decision Psychology Report — drop 'REPORT' in the comments and I'll send you the beta."
- platform: "social_post"
- goal: ["increase_comments", "generate_leads"]
- audience: "warm"

Expected Analysis Pattern:
- Strong hook about failure and curiosity → higher emotionalClarityScore
- Clear micro-CTA: comment 'REPORT' → lower frictionScore
- Good novelty angle → higher motivationMatchScore
- Slight resistance because 'beta' is not clearly explained → trustBreakpoints
- Typical scores: frictionScore ~25, trustScore ~70, decisionProbability ~0.8

EXAMPLE 3: Paid Ad (ad)
-------------------------
Input:
- raw_text: "Stop guessing your landing page performance. Get an AI-powered Decision Psychology Report in 60 seconds. See exactly where visitors hesitate — before you spend $1 more on ads."
- platform: "ad"
- goal: ["increase_clicks"]
- audience: "cold"

Expected Analysis Pattern:
- Clear benefit and time promise ('60 seconds') → lower frictionScore
- Strong pain point: wasting ad budget → higher motivationMatchScore
- Good specificity: 'see exactly where visitors hesitate' → higher trustScore
- Moderate resistance because there is no proof or brand credibility → trustBreakpoints
- Typical scores: frictionScore ~30, trustScore ~75, decisionProbability ~0.85

EXAMPLE 4: Sales Page (sales_page)
------------------------------------
Input:
- raw_text: "For years, you've watched campaigns underperform and had no idea why. You tried changing headlines, colors, and CTAs — but nothing was consistent. In this page, I'll show you how Decision Psychology Reports helped 137 marketers finally see the invisible friction inside their funnels..."
- platform: "sales_page"
- goal: ["increase_sales"]
- audience: "warm"

Expected Analysis Pattern:
- Good story-driven opening → higher emotionalClarityScore
- Specific number ('137 marketers') → higher trustScore
- Good empathy with the reader's struggle → higher motivationMatchScore
- Still low clarity on what the product exactly is in the first paragraph → cognitiveOverloadFactors
- Typical scores: frictionScore ~35, trustScore ~70, decisionProbability ~0.70

Use these patterns as guidance, but always analyze the actual content you receive rather than applying these scores mechanically.
"""

OUTPUT_REQUIREMENTS_MESSAGE = (
    "OUTPUT REQUIREMENTS:\n"
    "- Return ONLY valid JSON that follows the CognitiveFrictionResult schema described in the system prompt.\n"
    "- Always include friction analysis fields (keyDecisionBlockers plus the supporting factor lists).\n"
    "- Always include an analysis summary via explanationSummary (3-6 sentences).\n"
    "- Always include at least three recommendedQuickWins plus recommendedDeepChanges.\n"
    "- Always include the psychology_dashboard with all 13 sections populated (this is the 'dimensions' requirement).\n"
    "- Never include markdown or text outside the JSON object."
)

FIX_JSON_RETRY_MESSAGE = (
    "Fix JSON format. The previous response was not valid JSON. Return ONLY valid JSON that follows the CognitiveFrictionResult "
    "schema, including friction analysis lists, analysis summary, quick fixes, and the psychology_dashboard with all 13 sections."
)

PSYCHOLOGY_DASHBOARD_KEYS = [
    "personality_activation",
    "cognitive_style",
    "emotional_response",
    "decision_frame",
    "trust_dynamics",
    "motivation_style",
    "cognitive_load",
    "behavioral_prediction",
    "attention_map",
    "emotional_triggers",
    "memory_activation",
    "risk_perception",
    "cta_match",
]

TOP_LEVEL_DEFAULTS: Dict[str, Any] = {
    "frictionScore": 50.0,
    "trustScore": 50.0,
    "emotionalClarityScore": 50.0,
    "motivationMatchScore": 50.0,
    "decisionProbability": 0.5,
    "conversionLiftEstimate": 0.0,
    "keyDecisionBlockers": [],
    "emotionalResistanceFactors": [],
    "cognitiveOverloadFactors": [],
    "trustBreakpoints": [],
    "motivationMisalignments": [],
    "recommendedQuickWins": [],
    "recommendedDeepChanges": [],
    "explanationSummary": "Analysis completed.",
}

STRING_LIST_FIELDS = [
    "keyDecisionBlockers",
    "emotionalResistanceFactors",
    "cognitiveOverloadFactors",
    "trustBreakpoints",
    "motivationMisalignments",
    "recommendedQuickWins",
    "recommendedDeepChanges",
]


class InvalidAIResponseError(Exception):
    """Raised when the AI output cannot be coerced into the expected schema."""

    def __init__(self, raw_output: str):
        super().__init__("AI returned invalid structure")
        self.raw_output = raw_output


def _clamp_int(value: float) -> int:
    """Clamp a numeric value into 0-100 and convert to int."""
    return int(max(0, min(100, round(value))))


def build_psychology_dashboard_stub(
    friction_score: float,
    trust_score: float,
    summary: str,
    hotspots: Optional[List[str]] = None,
    friction_points: Optional[List[str]] = None,
) -> PsychologyDashboard:
    """
    Build a structured psychology dashboard using heuristics when the model output
    is unavailable (fallback) or when we need a deterministic visual-only result.
    """

    hotspots = hotspots or ["Hero headline", "Primary CTA"]
    friction_points = friction_points or ["Trust signals", "Proof placement"]

    dominant_profile = "Evidence-Seeking Thinker" if trust_score < 60 else "Decisive Optimizer"
    cognitive_style_type = "analytical" if friction_score >= 55 else "intuitive"

    curiosity = _clamp_int(70 - friction_score / 3)
    excitement = _clamp_int(trust_score / 1.5)
    motivation = _clamp_int(65 - friction_score / 4 + trust_score / 5)
    anxiety = _clamp_int(30 + friction_score / 2 - trust_score / 5)
    confusion = _clamp_int(friction_score / 1.6)
    trust_emotion = _clamp_int(trust_score)

    convert = _clamp_int((trust_score + (100 - friction_score)) / 2)
    hesitate = _clamp_int((friction_score + (100 - trust_score)) / 2)
    bounce = _clamp_int(max(15, friction_score - trust_score / 2))
    postpone = _clamp_int(max(0, 100 - convert - bounce))

    risk_level = _clamp_int((100 - trust_score) * 0.6 + friction_score * 0.6)

    return PsychologyDashboard(
        personality_activation={
            "O": _clamp_int(60 - friction_score / 5),
            "C": _clamp_int(55 + trust_score / 6),
            "E": _clamp_int(50 - friction_score / 4 + trust_score / 8),
            "A": _clamp_int(55),
            "N": _clamp_int(45 + friction_score / 5),
            "dominant_profile": dominant_profile,
            "explanation": "Fallback profile derived from friction/trust trends.",
        },
        cognitive_style={
            "type": cognitive_style_type,
            "overload_risk": _clamp_int(friction_score),
            "ambiguity_aversion": _clamp_int(60 + friction_score / 4),
            "explanation": "Generated heuristically to preserve dashboard completeness.",
        },
        emotional_response={
            "curiosity": curiosity,
            "excitement": excitement,
            "motivation": motivation,
            "anxiety": anxiety,
            "confusion": confusion,
            "trust": trust_emotion,
        },
        decision_frame={
            "mode": "loss_avoidance" if trust_score < 55 else "gain_seeking",
            "risk_style": "risk_averse" if trust_score < 55 else "moderate",
            "decision_tendency": "hesitate" if friction_score >= 50 else "move_forward",
            "explanation": summary,
        },
        trust_dynamics={
            "visual_trust": _clamp_int(trust_score - 5),
            "institutional_trust": _clamp_int(trust_score),
            "social_trust": _clamp_int(trust_score - 10),
            "skepticism": _clamp_int(40 + friction_score / 2),
        },
        motivation_style={
            "primary": "Achievement" if trust_score >= 55 else "Security",
            "secondary": "Security" if trust_score >= 55 else "Clarity",
            "explanation": "Auto-generated motivation narrative for fallback reporting.",
        },
        cognitive_load={
            "clarity_score": _clamp_int(100 - friction_score),
            "overload_score": _clamp_int(friction_score),
            "ambiguity_score": _clamp_int(50 + friction_score / 3),
        },
        behavioral_prediction={
            "convert": convert,
            "hesitate": hesitate,
            "bounce": bounce,
            "postpone": postpone,
            "summary": summary,
        },
        attention_map={
            "hotspots": hotspots,
            "friction_points": friction_points,
        },
        emotional_triggers={
            "activated": ["Curiosity", "Growth"],
            "missing": ["Safety"] if trust_score < 60 else ["Urgency"],
        },
        memory_activation={
            "semantic": _clamp_int(55 + trust_score / 6),
            "emotional": _clamp_int(excitement),
            "pattern": _clamp_int(45 + (100 - friction_score) / 5),
        },
        risk_perception={
            "risk_level": risk_level,
            "uncertainty_points": [
                "Fallback dashboard generated due to upstream response issues."
            ],
        },
        cta_match={
            "fit_score": _clamp_int((100 - friction_score + trust_score) / 2),
            "clarity": _clamp_int(60 - friction_score / 3 + trust_score / 5),
            "motivation_alignment": _clamp_int(55 + motivation / 5),
            "action_probability": convert,
        },
    )


def _extract_json_payload(raw_content: str, context: str) -> Dict[str, Any]:
    """Extract and parse JSON from a raw model response string."""
    if not raw_content:
        raise ValueError(f"{context} returned an empty response.")

    trimmed = raw_content.strip()
    if trimmed.startswith("```json"):
        trimmed = trimmed[7:]
        closing = trimmed.find("```")
        if closing != -1:
            trimmed = trimmed[:closing].strip()
    elif trimmed.startswith("```"):
        trimmed = trimmed[3:]
        closing = trimmed.find("```")
        if closing != -1:
            trimmed = trimmed[:closing].strip()

    if not trimmed:
        raise ValueError(f"{context} response became empty after trimming.")

    if trimmed[0] not in "{[":
        preview = trimmed[:80]
        raise ValueError(f"{context} is not valid JSON. Preview: {preview!r}")

    if trimmed[0] == "{":
        brace_count = 0
        end_index = None
        for idx, char in enumerate(trimmed):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_index = idx + 1
                    break
        if end_index is not None:
            trimmed = trimmed[:end_index]

    return json.loads(trimmed)


def _validate_psychology_dashboard_structure(payload: Dict[str, Any]) -> None:
    """Ensure the psychology_dashboard dictionary includes all 13 required sections."""
    dashboard = payload.get("psychology_dashboard")
    if not isinstance(dashboard, dict):
        raise ValueError("psychology_dashboard missing or not an object.")

    missing = [key for key in PSYCHOLOGY_DASHBOARD_KEYS if key not in dashboard]
    if missing:
        raise ValueError(
            f"psychology_dashboard missing sections: {', '.join(sorted(missing))}"
        )

    for key in PSYCHOLOGY_DASHBOARD_KEYS:
        if dashboard[key] in (None, "", []):
            raise ValueError(f"psychology_dashboard.{key} must be populated.")


# ====================================================
# INPUT/OUTPUT SCHEMAS
# ====================================================

class CognitiveFrictionInput(BaseModel):
    """Input schema for cognitive friction analysis"""
    raw_text: str = Field(default="", description="The content/post/copy to analyze (empty string allowed if image is provided)")
    platform: Literal[
        "landing_page",
        "social_post",
        "ad",
        "sales_page",
        "lead_magnet",
        "engagement",
        "email",
    ] = Field(..., description="Platform type for analysis")
    goal: List[str] = Field(..., description="Goals: clicks, leads, sales, engagement, etc.")
    audience: str = Field(..., description="Audience type: cold, warm, retargeting, etc.")
    language: str = Field(default="en", description="Language code: en, tr, fa, etc.")
    meta: Optional[Any] = Field(default=None, description="Optional metadata for future use")


class CognitiveFrictionResult(BaseModel):
    """Output schema for cognitive friction analysis results"""
    frictionScore: float = Field(..., ge=0, le=100, description="Overall cognitive friction (0-100)")
    trustScore: float = Field(..., ge=0, le=100, description="Perceived trust level (0-100)")
    emotionalClarityScore: float = Field(..., ge=0, le=100, description="Emotional clarity & resonance (0-100)")
    motivationMatchScore: float = Field(..., ge=0, le=100, description="Alignment with user motivation (0-100)")
    decisionProbability: float = Field(..., ge=0, le=1, description="Likelihood user will decide/act (0-1)")
    conversionLiftEstimate: float = Field(..., ge=-100, le=100, description="% improvement if issues fixed (-100 to +100)")
    keyDecisionBlockers: List[str] = Field(default_factory=list, description="Main blockers (bulleted reasons)")
    emotionalResistanceFactors: List[str] = Field(default_factory=list, description="Emotional resistance factors")
    cognitiveOverloadFactors: List[str] = Field(default_factory=list, description="Cognitive overload factors")
    trustBreakpoints: List[str] = Field(default_factory=list, description="Trust breakpoints")
    motivationMisalignments: List[str] = Field(default_factory=list, description="Motivation misalignments")
    recommendedQuickWins: List[str] = Field(default_factory=list, description="Actionable quick fixes")
    recommendedDeepChanges: List[str] = Field(default_factory=list, description="Deeper structural changes")
    explanationSummary: str = Field(..., description="3-6 sentences, plain language summary of the analysis")
    psychology_dashboard: PsychologyDashboard = Field(
        ...,
        description="13-dimension psychology dashboard for the analyzed landing page",
    )
    psychology: Optional[PsychologyAnalysisResult] = Field(
        default=None,
        description="Full psychology analysis payload including advanced view.",
    )


def _default_psychology_dashboard() -> Dict[str, Any]:
    """Return a zeroed-out psychology dashboard placeholder."""
    return {
        "personality_activation": {
            "O": 0,
            "C": 0,
            "E": 0,
            "A": 0,
            "N": 0,
            "dominant_profile": "Undetermined",
            "explanation": "",
        },
        "cognitive_style": {
            "type": "analytical",
            "overload_risk": 0,
            "ambiguity_aversion": 0,
            "explanation": "",
        },
        "emotional_response": {
            "curiosity": 0,
            "excitement": 0,
            "motivation": 0,
            "anxiety": 0,
            "confusion": 0,
            "trust": 0,
        },
        "decision_frame": {
            "mode": "neutral",
            "risk_style": "moderate",
            "decision_tendency": "hesitate",
            "explanation": "",
        },
        "trust_dynamics": {
            "visual_trust": 0,
            "institutional_trust": 0,
            "social_trust": 0,
            "skepticism": 0,
        },
        "motivation_style": {
            "primary": "Unspecified",
            "secondary": "",
            "explanation": "",
        },
        "cognitive_load": {
            "clarity_score": 0,
            "overload_score": 0,
            "ambiguity_score": 0,
        },
        "behavioral_prediction": {
            "convert": 0,
            "hesitate": 0,
            "bounce": 0,
            "postpone": 0,
            "summary": "",
        },
        "attention_map": {
            "hotspots": [],
            "friction_points": [],
        },
        "emotional_triggers": {
            "activated": [],
            "missing": [],
        },
        "memory_activation": {
            "semantic": 0,
            "emotional": 0,
            "pattern": 0,
        },
        "risk_perception": {
            "risk_level": 0,
            "uncertainty_points": [],
        },
        "cta_match": {
            "fit_score": 0,
            "clarity": 0,
            "motivation_alignment": 0,
            "action_probability": 0,
        },
    }


SECTION_ENUM_OPTIONS = {
    ("cognitive_style", "type"): {"analytical", "intuitive", "overloaded", "mixed"},
    ("decision_frame", "mode"): {"gain_seeking", "loss_avoidance", "neutral"},
    ("decision_frame", "risk_style"): {"risk_averse", "risk_taking", "moderate"},
    ("decision_frame", "decision_tendency"): {
        "move_forward",
        "hesitate",
        "postpone",
        "bounce",
    },
}


def _log_validation_warning(message: str) -> None:
    logger.warning("[validation] %s", message)


def _coerce_float(value: Any, field: str, default: float) -> float:
    if value is None:
        _log_validation_warning(f"{field} missing; defaulting to {default}.")
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            _log_validation_warning(f"{field} empty string; defaulting to {default}.")
            return default
        try:
            return float(stripped)
        except ValueError:
            _log_validation_warning(
                f"{field} received non-numeric string '{value}'; defaulting to {default}."
            )
            return default
    _log_validation_warning(
        f"{field} received invalid type {type(value).__name__}; defaulting to {default}."
    )
    return default


def _normalize_numeric(value: Any, field: str, default: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
    numeric = _coerce_float(value, field, default)
    if numeric < min_value:
        _log_validation_warning(
            f"{field} below minimum ({numeric} < {min_value}); clamping."
        )
        numeric = min_value
    if numeric > max_value:
        _log_validation_warning(
            f"{field} above maximum ({numeric} > {max_value}); clamping."
        )
        numeric = max_value
    return numeric


def _normalize_probability(value: Any) -> float:
    prob = _coerce_float(
        value,
        "decisionProbability",
        TOP_LEVEL_DEFAULTS["decisionProbability"],
    )
    if prob > 1:
        _log_validation_warning(
            f"decisionProbability appears to be percentage ({prob}); scaling to 0-1."
        )
        prob = prob / 100.0
    prob = max(0.0, min(1.0, prob))
    return round(prob, 4)


def _normalize_conversion_lift(value: Any) -> float:
    lift = _coerce_float(
        value,
        "conversionLiftEstimate",
        TOP_LEVEL_DEFAULTS["conversionLiftEstimate"],
    )
    return round(max(-100.0, min(100.0, lift)), 2)


def _ensure_string(value: Any, field: str, default: str = "") -> str:
    if value is None:
        _log_validation_warning(f"{field} missing; defaulting to '{default}'.")
        return default
    if isinstance(value, str):
        return value
    _log_validation_warning(
        f"{field} expected string but received {type(value).__name__}; coercing."
    )
    return str(value)


def _ensure_string_list(value: Any, field: str) -> List[str]:
    if value is None:
        _log_validation_warning(f"{field} missing; defaulting to empty list.")
        return []
    if isinstance(value, list):
        sanitized: List[str] = []
        for idx, item in enumerate(value):
            if item is None:
                continue
            if not isinstance(item, str):
                _log_validation_warning(
                    f"{field}[{idx}] expected string but received {type(item).__name__}; coercing."
                )
                sanitized.append(str(item))
            else:
                sanitized.append(item)
        return sanitized
    if isinstance(value, str):
        _log_validation_warning(f"{field} provided as string; wrapping in list.")
        return [value]
    _log_validation_warning(
        f"{field} expected list of strings but received {type(value).__name__}; defaulting to empty list."
    )
    return []


def _normalize_top_level_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    payload["frictionScore"] = _normalize_numeric(
        data.get("frictionScore"),
        "frictionScore",
        TOP_LEVEL_DEFAULTS["frictionScore"],
    )
    payload["trustScore"] = _normalize_numeric(
        data.get("trustScore"),
        "trustScore",
        TOP_LEVEL_DEFAULTS["trustScore"],
    )
    payload["emotionalClarityScore"] = _normalize_numeric(
        data.get("emotionalClarityScore"),
        "emotionalClarityScore",
        TOP_LEVEL_DEFAULTS["emotionalClarityScore"],
    )
    payload["motivationMatchScore"] = _normalize_numeric(
        data.get("motivationMatchScore"),
        "motivationMatchScore",
        TOP_LEVEL_DEFAULTS["motivationMatchScore"],
    )
    payload["decisionProbability"] = _normalize_probability(
        data.get("decisionProbability")
    )
    payload["conversionLiftEstimate"] = _normalize_conversion_lift(
        data.get("conversionLiftEstimate")
    )

    for list_field in STRING_LIST_FIELDS:
        payload[list_field] = _ensure_string_list(data.get(list_field), list_field)

    payload["explanationSummary"] = _ensure_string(
        data.get("explanationSummary"),
        "explanationSummary",
        TOP_LEVEL_DEFAULTS["explanationSummary"],
    )
    payload["psychology_dashboard"] = _normalize_psychology_dashboard(
        data.get("psychology_dashboard")
    )
    return payload


def _normalize_psychology_dashboard(dashboard: Any) -> Dict[str, Any]:
    defaults = _default_psychology_dashboard()
    if not isinstance(dashboard, dict):
        _log_validation_warning(
            "psychology_dashboard missing or invalid; inserting placeholder."
        )
        return defaults

    normalized: Dict[str, Any] = {}
    for section, section_defaults in defaults.items():
        section_data = dashboard.get(section)
        if not isinstance(section_data, dict):
            _log_validation_warning(
                f"psychology_dashboard.{section} missing; inserting placeholder section."
            )
            normalized[section] = section_defaults
            continue
        normalized[section] = _normalize_dashboard_section(
            section, section_data, section_defaults
        )
    return normalized


def _normalize_dashboard_section(
    section_name: str, section_data: Dict[str, Any], defaults: Dict[str, Any]
) -> Dict[str, Any]:
    normalized_section: Dict[str, Any] = {}
    for field_name, default_value in defaults.items():
        full_field = f"psychology_dashboard.{section_name}.{field_name}"
        value = section_data.get(field_name, default_value)
        if isinstance(default_value, list):
            normalized_section[field_name] = _ensure_string_list(value, full_field)
        elif isinstance(default_value, (int, float)):
            normalized_value = _normalize_numeric(value, full_field, default_value)
            normalized_section[field_name] = int(round(normalized_value))
        else:
            coerced = _ensure_string(value, full_field, default_value)
            enum_key = (section_name, field_name)
            if enum_key in SECTION_ENUM_OPTIONS and coerced not in SECTION_ENUM_OPTIONS[enum_key]:
                _log_validation_warning(
                    f"{full_field} used invalid option '{coerced}'; defaulting to '{default_value}'."
                )
                coerced = default_value
            normalized_section[field_name] = coerced
    return normalized_section


def _auto_repair_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    valid_fields = set(CognitiveFrictionResult.model_fields.keys())
    repaired: Dict[str, Any] = {
        key: deepcopy(value)
        for key, value in data.items()
        if key in valid_fields
    }

    for key, default in TOP_LEVEL_DEFAULTS.items():
        if key not in repaired:
            _log_validation_warning(
                f"Auto-filling missing field '{key}' during repair."
            )
            repaired[key] = deepcopy(default) if isinstance(default, list) else default

    if "psychology_dashboard" not in repaired or not isinstance(
        repaired["psychology_dashboard"], dict
    ):
        _log_validation_warning(
            "Auto-filling missing psychology_dashboard during repair."
        )
        repaired["psychology_dashboard"] = _default_psychology_dashboard()
    else:
        repaired["psychology_dashboard"] = _normalize_psychology_dashboard(
            repaired["psychology_dashboard"]
        )

    return repaired


def _parse_model_response_with_retry(
    client: OpenAI, model: str, raw_content: str
) -> Tuple[Dict[str, Any], str]:
    try:
        return json.loads(raw_content), raw_content
    except json.JSONDecodeError as primary_error:
        _log_validation_warning(
            f"Initial JSON parsing failed; attempting fix prompt: {primary_error}"
        )

        retry_messages = [
            {
                "role": "system",
                "content": "You are a JSON repair assistant that outputs strictly valid JSON.",
            },
            {
                "role": "user",
                "content": f"{FIX_JSON_RETRY_MESSAGE}\n\nBroken JSON:\n{raw_content}",
            },
        ]
        logger.warning("[validation] Retrying JSON repair via fix prompt.")
        retry_response = client.chat.completions.create(
            model=model,
            messages=retry_messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        fixed_content = retry_response.choices[0].message.content
        try:
            return json.loads(fixed_content), fixed_content
        except json.JSONDecodeError as retry_error:
            logger.error(
                "[validation] JSON parsing failed after retry: %s", retry_error
            )
            raise InvalidAIResponseError(raw_output=raw_content) from retry_error


def validate_cognitive_response(raw_dict: Dict[str, Any]) -> CognitiveFrictionResult:
    """
    Validate and coerce the raw dictionary into a CognitiveFrictionResult.
    """
    if not isinstance(raw_dict, dict):
        raise ValueError("AI response must be a JSON object.")

    normalized_payload = _normalize_top_level_payload(deepcopy(raw_dict))

    try:
        return CognitiveFrictionResult(**normalized_payload)
    except ValidationError as validation_error:
        logger.warning(
            "[validation] Pydantic validation failed; attempting auto-repair: %s",
            validation_error,
        )
        repaired_payload = _auto_repair_payload(normalized_payload)
        try:
            return CognitiveFrictionResult(**repaired_payload)
        except ValidationError as final_error:
            logger.error(
                "[validation] Auto-repair failed; response still invalid: %s",
                final_error,
            )
            raise

# ====================================================
# VISUAL-ONLY ANALYSIS BUILDER
# ====================================================

def build_visual_only_analysis(
    image_score: Optional[float],
    extracted_text_summary: str = "",
) -> CognitiveFrictionResult:
    """
    Build a cognitive friction analysis for VISUAL-ONLY mode, based primarily on image_score.
    This MUST NOT claim that 'no content' exists on the page.
    
    Args:
        image_score: Visual trust score (0-100) from local image model
        extracted_text_summary: Optional summary of text extracted from image by GPT
    
    Returns:
        CognitiveFrictionResult with visual-based scores
    """
    # Fallback image_score
    score = int(round(image_score or 50))
    if score < 0:
        score = 0
    if score > 100:
        score = 100
    
    # Simple heuristic: higher visual quality → lower friction
    # Invert: image_score 0-100 maps to friction 100-0
    decision_friction_score = max(0, min(100, 100 - score))
    
    # Trust score correlates with visual quality
    trust_score = max(30, min(100, score))
    
    # Emotional clarity: moderate for visuals (depends on design)
    emotional_clarity_score = max(40, min(80, score))
    
    # Motivation match: moderate (needs text analysis for accurate score)
    motivation_match_score = 50.0
    
    # Decision probability: based on friction and trust
    decision_probability = max(0.2, min(0.8, (100 - decision_friction_score + trust_score) / 200.0))
    
    # Conversion lift: positive if visual is good
    conversion_lift_estimate = max(-50, min(50, (score - 50) * 0.5))
    
    # Build blockers based on visual quality
    if score < 50:
        key_blockers = [
            "Visual hierarchy may not clearly direct attention to the primary call-to-action.",
            "Trust signals (such as testimonials, logos, or guarantees) may not be visually prominent enough.",
            "The layout may lack clear visual flow that guides users toward conversion.",
        ]
        emotional_resistance = [
            "Visual design may not create sufficient emotional connection or urgency.",
            "Color scheme and imagery may not align with the target audience's expectations.",
        ]
        trust_breakpoints = [
            "Visual trust signals are not prominent enough to build confidence.",
        ]
    else:
        key_blockers = [
            "Consider optimizing visual hierarchy to further emphasize the call-to-action.",
            "Ensure trust signals remain visible and prominent throughout the user journey.",
        ]
        emotional_resistance = []
        trust_breakpoints = []
    
    summary = (
        "This analysis is based on the visual design and layout of the page. "
        "The Decision Friction Score reflects how effectively the visual hierarchy, "
        "call-to-action placement, and trust cues guide users toward action. "
    )
    
    if extracted_text_summary:
        summary += f"Text content was extracted from the image: {extracted_text_summary[:200]}"
    else:
        summary += "Visual elements were analyzed to assess conversion potential."
    
    dashboard_summary = (
        "Visual cues guide initial attention to the hero area, but users slow down when proof and trust markers "
        "are not clearly visible. Emphasize CTA clarity and ensure supporting evidence is close to the action point."
    )
    dashboard = build_psychology_dashboard_stub(
        friction_score=decision_friction_score,
        trust_score=trust_score,
        summary=dashboard_summary,
        hotspots=["Hero section", "Primary CTA"],
        friction_points=["Trust badges", "CTA contrast"],
    )

    return CognitiveFrictionResult(
        frictionScore=float(decision_friction_score),
        trustScore=float(trust_score),
        emotionalClarityScore=float(emotional_clarity_score),
        motivationMatchScore=float(motivation_match_score),
        decisionProbability=decision_probability,
        conversionLiftEstimate=conversion_lift_estimate,
        keyDecisionBlockers=key_blockers,
        emotionalResistanceFactors=emotional_resistance,
        cognitiveOverloadFactors=[],
        trustBreakpoints=trust_breakpoints,
        motivationMisalignments=[],
        recommendedQuickWins=[
            "Ensure the main headline and CTA are visually dominant and easy to identify at a glance.",
            "Make trust elements (logos, testimonials, guarantees) clearly visible above the fold.",
            "Use visual contrast to guide attention toward the primary action.",
        ],
        recommendedDeepChanges=[
            "Conduct A/B testing on visual hierarchy and CTA placement.",
            "Optimize color psychology and imagery to better match audience expectations.",
            "Improve visual flow to reduce cognitive load and increase clarity.",
        ],
        explanationSummary=summary,
        psychology_dashboard=dashboard,
    )


# ====================================================
# MAIN ANALYSIS FUNCTION
# ====================================================

def analyze_cognitive_friction(
    input_data: CognitiveFrictionInput,
    image_base64: Optional[str] = None,
    image_mime: Optional[str] = None,
    image_score: Optional[float] = None,
    model_override: Optional[str] = None,
) -> CognitiveFrictionResult:
    """
    Analyze cognitive friction and decision psychology for given content.
    
    This function:
    1. Constructs a user message with content and context as JSON
    2. Calls OpenAI API with the cognitive friction system prompt
    3. Parses and validates the JSON response
    4. Returns structured CognitiveFrictionResult
    
    Args:
        input_data: CognitiveFrictionInput with raw_text, platform, goal, audience, language, meta
    
    Returns:
        CognitiveFrictionResult with all scores and explanations
    
    Raises:
        ValueError: If API key is missing or response parsing fails
        Exception: For other API or parsing errors
    """
    client = get_client()
    
    # Determine analysis mode
    has_image = image_base64 is not None and image_mime is not None
    has_text = input_data.raw_text and input_data.raw_text.strip()
    
    print(f"[cognitive_friction] Analysis mode: has_image={has_image}, has_text={has_text}")
    
    # Validate: at least one must be provided
    if not has_image and not has_text:
        raise ValueError("Either text (raw_text) or image must be provided for analysis. Both are empty.")
    
    # Validate: at least one must be provided
    if not has_image and not has_text:
        raise ValueError("Either text (raw_text) or image must be provided for analysis.")
    
    # Get platform-specific context
    platform_context = build_platform_context(input_data.platform)
    
    if has_image:
        # Image mode: Use Vision API (with or without text)
        user_content = []
        
        if has_text:
            # Both image and text: Combine them
            text_instruction = (
                f"{platform_context}\n\n"
                "You have BOTH:\n"
                "1. An IMAGE/screenshot of the content\n"
                "2. Additional TEXT content provided separately\n"
                "\n"
                "ANALYSIS STEPS:\n"
                "STEP 1: Carefully read and extract ALL text visible in the image.\n"
                "STEP 2: Combine the extracted image text with the provided text below.\n"
                "STEP 3: Analyze the combined content using the decision psychology framework.\n"
                "\n"
                "Extract from IMAGE:\n"
                "- All headlines, subheadings, and body text visible\n"
                "- Call-to-action (CTA) buttons and text\n"
                "- Trust signals (testimonials, logos, guarantees)\n"
                "- Value propositions and benefits\n"
                "- Any other visible text content\n"
                "\n"
                "Additional TEXT provided separately:\n"
                f"{input_data.raw_text}\n"
                "\n"
                "After extracting text from image and combining with provided text, analyze everything for cognitive friction, trust, emotional clarity, and decision blockers.\n"
                "\n"
                f"Context: Platform={input_data.platform}, Goal={input_data.goal}, Audience={input_data.audience}, Language={input_data.language}\n\n"
                f"{OUTPUT_REQUIREMENTS_MESSAGE}"
            )
        else:
            # Image-only mode: Extract text from image
            text_instruction = (
                f"{platform_context}\n\n"
                "IMPORTANT: You are analyzing a screenshot/image.\n"
                "You must READ the image and extract ALL visible text.\n"
                "\n"
                "STEP 1: Carefully read and extract ALL text visible in the image:\n"
                "- All headlines, subheadings, and body text\n"
                "- Call-to-action (CTA) buttons and text\n"
                "- Trust signals (testimonials, logos, guarantees)\n"
                "- Value propositions and benefits\n"
                "- Any other visible text content\n"
                "\n"
                "STEP 2: Analyze the extracted text using the decision psychology framework.\n"
                "\n"
                "CRITICAL: If you can see text in the image, extract it and analyze it. "
                "DO NOT say the page is 'empty' or 'has no content' if there is visible text in the image.\n"
                "\n"
                f"Context: Platform={input_data.platform}, Goal={input_data.goal}, Audience={input_data.audience}, Language={input_data.language}\n\n"
                f"{OUTPUT_REQUIREMENTS_MESSAGE}"
            )
        
        user_content.append({"type": "text", "text": text_instruction})
        
        # Add image to Vision API
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{image_mime};base64,{image_base64}"
            }
        })
        
        messages = [
            {"role": "system", "content": COGNITIVE_FRICTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]
        
        # Use Vision-capable model
        model = "gpt-4o-mini"  # Supports vision
        if model_override:
            model = model_override
        print(f"[cognitive_friction] Using Vision API with model={model}")
        
    else:
        # Text-only mode: Use regular API (no image)
        # Build user message with platform context
        platform_context = build_platform_context(input_data.platform)
        user_message_text = (
            f"{platform_context}\n\n"
            f"Content to analyze:\n{input_data.raw_text}\n\n"
            f"Context: Platform={input_data.platform}, Goal={input_data.goal}, Audience={input_data.audience}, Language={input_data.language}\n\n"
            f"{OUTPUT_REQUIREMENTS_MESSAGE}"
        )
        
        messages = [
            {"role": "system", "content": COGNITIVE_FRICTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message_text}
        ]
        
        model = "gpt-4o-mini"
        if model_override:
            model = model_override
        print(f"[cognitive_friction] Using text-only API with model={model}, platform={input_data.platform}")
    
    # Call OpenAI API
    try:
        print(f"[cognitive_friction] Calling OpenAI API with model={model}, has_image={has_image}, has_text={has_text}")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"}  # Force JSON response
        )
        print(f"[cognitive_friction] OpenAI API response received")
        
        raw_content = response.choices[0].message.content
        print(f"[cognitive_friction] Raw response length: {len(raw_content)} characters")
        print(f"[cognitive_friction] Raw response preview: {raw_content[:300]}...")
        
        parsed_payload, parsed_raw_content = _parse_model_response_with_retry(
            client, model, raw_content
        )
        try:
            result = validate_cognitive_response(parsed_payload)
        except (ValidationError, ValueError) as validation_error:
            logger.error(
                "[validation] Unable to coerce AI response into schema: %s",
                validation_error,
            )
            raise InvalidAIResponseError(raw_output=parsed_raw_content) from validation_error

        print(f"[cognitive_friction] ✅ Successfully parsed JSON response from OpenAI")
        print(
            f"[cognitive_friction] Result: friction={result.frictionScore}, trust={result.trustScore}, decisionProb={result.decisionProbability}"
        )
        print(
            f"[cognitive_friction] Blockers count: {len(result.keyDecisionBlockers)}"
        )

        # If image-only mode and the AI still says "empty", override with visual-based analysis
        visual_only_mode = has_image and not has_text
        if visual_only_mode:
            # Check if AI returned "empty page" response even though an image exists
            empty_phrases = [
                "empty",
                "no content",
                "completely empty",
                "no visible text",
                "nothing to analyze",
                "blank page",
                "no copy",
                "no readable text",
            ]

            def contains_empty_phrase(text: str) -> bool:
                text_lower = (text or "").lower()
                return any(phrase in text_lower for phrase in empty_phrases)

            blockers_flag = any(
                contains_empty_phrase(blocker) for blocker in result.keyDecisionBlockers
            )
            summary_flag = contains_empty_phrase(result.explanationSummary or "")
            score_flag = result.frictionScore >= 90 and result.trustScore <= 10

            if blockers_flag or summary_flag or score_flag:
                print(
                    "⚠️ AI returned 'empty page' cues in visual mode. Overriding with visual-based analysis."
                )
                # Override with visual-based analysis using image_score
                visual_result = build_visual_only_analysis(
                    image_score=image_score,
                    extracted_text_summary=(
                        result.explanationSummary[:200]
                        if result.explanationSummary
                        else ""
                    ),
                )
                return visual_result

        return result
    
    except InvalidAIResponseError:
        raise
    except Exception as e:
        print(f"❌ Error in analyze_cognitive_friction: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
        # Return safe fallback
        return CognitiveFrictionResult(
            frictionScore=50.0,
            trustScore=50.0,
            emotionalClarityScore=50.0,
            motivationMatchScore=50.0,
            decisionProbability=0.5,
            conversionLiftEstimate=0.0,
            keyDecisionBlockers=[f"Error during analysis: {str(e)}"],
            emotionalResistanceFactors=[],
            cognitiveOverloadFactors=[],
            trustBreakpoints=[],
            motivationMisalignments=[],
            recommendedQuickWins=[],
            recommendedDeepChanges=[],
            explanationSummary=f"Analysis failed due to error: {str(e)}"
        )


# ====================================================
# DOCUMENTATION SUMMARY
# ====================================================

"""
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

