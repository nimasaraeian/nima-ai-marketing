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
from typing import List, Optional, Dict, Any
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
"""


# ====================================================
# INPUT/OUTPUT SCHEMAS
# ====================================================

class CognitiveFrictionInput(BaseModel):
    """Input schema for cognitive friction analysis"""
    raw_text: str = Field(..., description="The content/post/copy to analyze")
    platform: str = Field(..., description="Platform type: landing_page, instagram, linkedin, email, etc.")
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
# MAIN ANALYSIS FUNCTION
# ====================================================

def analyze_cognitive_friction(input_data: CognitiveFrictionInput) -> CognitiveFrictionResult:
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
    
    # Build user message as JSON
    user_message = json.dumps({
        "raw_text": input_data.raw_text,
        "platform": input_data.platform,
        "goal": input_data.goal,
        "audience": input_data.audience,
        "language": input_data.language,
        "meta": input_data.meta,
    })
    
    # Call OpenAI API
    try:
        messages = [
            {"role": "system", "content": COGNITIVE_FRICTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"}  # Force JSON response
        )
        
        raw_content = response.choices[0].message.content
        
        # Parse JSON safely
        try:
            data = json.loads(raw_content)
            
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
            
            return CognitiveFrictionResult(**data)
            
        except json.JSONDecodeError:
            # Fallback: return a low-confidence default structure
            print(f"⚠️ JSON parsing error. Raw response: {raw_content[:200]}")
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

