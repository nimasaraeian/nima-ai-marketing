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
import os
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI

# Load environment variables
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
else:
    load_dotenv()

# Initialize OpenAI client lazily
_client = None

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
    )


# ====================================================
# MAIN ANALYSIS FUNCTION
# ====================================================

def analyze_cognitive_friction(input_data: CognitiveFrictionInput, image_base64: Optional[str] = None, image_mime: Optional[str] = None, image_score: Optional[float] = None) -> CognitiveFrictionResult:
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
                f"Context: Platform={input_data.platform}, Goal={input_data.goal}, Audience={input_data.audience}, Language={input_data.language}"
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
                f"Context: Platform={input_data.platform}, Goal={input_data.goal}, Audience={input_data.audience}, Language={input_data.language}"
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
        print(f"[cognitive_friction] Using Vision API with model={model}")
        
    else:
        # Text-only mode: Use regular API (no image)
        # Build user message with platform context
        platform_context = build_platform_context(input_data.platform)
        user_message_text = (
            f"{platform_context}\n\n"
            f"Content to analyze:\n{input_data.raw_text}\n\n"
            f"Context: Platform={input_data.platform}, Goal={input_data.goal}, Audience={input_data.audience}, Language={input_data.language}"
        )
        
        messages = [
            {"role": "system", "content": COGNITIVE_FRICTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message_text}
        ]
        
        model = "gpt-4o-mini"
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
        
        # Parse JSON safely
        try:
            from json_utils import safe_parse_json
            data = safe_parse_json(raw_content, context="cognitive friction analysis")
            
            # Ensure decisionProbability is 0-1 (convert if 0-100)
            if "decisionProbability" in data:
                dp = data["decisionProbability"]
                if dp > 1:
                    data["decisionProbability"] = dp / 100.0
            
            # Ensure all required fields exist with defaults
            required_fields = {
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
                "explanationSummary": "Analysis completed."
            }
            
            for key, default_value in required_fields.items():
                if key not in data:
                    data[key] = default_value
            
            result = CognitiveFrictionResult(**data)
            print(f"[cognitive_friction] ✅ Successfully parsed JSON response from OpenAI")
            print(f"[cognitive_friction] Result: friction={result.frictionScore}, trust={result.trustScore}, decisionProb={result.decisionProbability}")
            print(f"[cognitive_friction] Blockers count: {len(result.keyDecisionBlockers)}")
            
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

                blockers_flag = any(contains_empty_phrase(blocker) for blocker in result.keyDecisionBlockers)
                summary_flag = contains_empty_phrase(result.explanationSummary or "")
                score_flag = result.frictionScore >= 90 and result.trustScore <= 10

                if blockers_flag or summary_flag or score_flag:
                    print("⚠️ AI returned 'empty page' cues in visual mode. Overriding with visual-based analysis.")
                    # Override with visual-based analysis using image_score
                    visual_result = build_visual_only_analysis(
                        image_score=image_score,
                        extracted_text_summary=result.explanationSummary[:200] if result.explanationSummary else ""
                    )
                    return visual_result
            
            return result
            
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: return a low-confidence default structure
            print(f"⚠️ JSON parsing error in cognitive friction analysis: {str(e)}")
            print(f"⚠️ Raw response preview: {raw_content[:500] if 'raw_content' in locals() else 'No response'}")
            import traceback
            traceback.print_exc()
            return CognitiveFrictionResult(
                frictionScore=50.0,
                trustScore=50.0,
                emotionalClarityScore=50.0,
                motivationMatchScore=50.0,
                decisionProbability=0.5,
                conversionLiftEstimate=0.0,
                keyDecisionBlockers=["Model failed to return valid JSON. Using fallback result."],
                emotionalResistanceFactors=[],
                cognitiveOverloadFactors=[],
                trustBreakpoints=[],
                motivationMisalignments=[],
                recommendedQuickWins=[],
                recommendedDeepChanges=[],
                explanationSummary="The AI model did not return valid JSON, so this is a fallback neutral result."
            )
    
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

