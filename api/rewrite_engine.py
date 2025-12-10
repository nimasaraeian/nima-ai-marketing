"""
AI Copy Rewrite Engine

This module provides a specialized AI engine for rewriting marketing text
into 5 different professional versions based on behavioral psychology and
business decision science.

Location: api/rewrite_engine.py
API Endpoint: POST /api/brain/rewrite (in main.py)
"""

import json
import os
import sys
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI

# Add api directory to path for imports
api_dir = Path(__file__).parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

# Import models - using relative import since we're in api/ folder
try:
    from models.rewrite_models import RewriteInput, RewriteOutput
except ImportError:
    # Fallback to absolute import if relative doesn't work
    from api.models.rewrite_models import RewriteInput, RewriteOutput

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
        # Set timeout to 300 seconds (5 minutes) for long-running requests
        _client = OpenAI(api_key=api_key, timeout=300.0, max_retries=3)
    return _client


# ====================================================
# SYSTEM PROMPT - Rewrite Engine
# ====================================================

REWRITE_SYSTEM_PROMPT = """You are an AI Copy Rewrite Engine specialized in behavioral psychology, cognitive friction reduction, trust-building, and conversion optimization.

Your mission:
Rewrite marketing text into 5 different professional versions, each optimized for different psychological triggers and decision patterns.

You MUST apply:
- Consumer psychology principles
- Cognitive friction reduction techniques
- Trust-building strategies
- Behavioral economics insights
- Clear benefit communication
- Proof-driven writing
- CTA optimization

REWRITE RULES (STRICT):
- NO hype language (avoid "revolutionary", "game-changing", "amazing" without proof)
- NO generic claims (avoid "best", "top", "leading" without evidence)
- Clear value delivery (specific, measurable benefits)
- Realistic, measurable statements (use numbers, facts, examples)
- 8th-grade readability (simple, clear language)
- High trust score (credible, honest, specific)
- High clarity score (unambiguous, easy to understand)

5 REWRITE STYLES:

1) SOFT TRUST-BASED VERSION:
   - Build trust gradually
   - Use reassurance language
   - Reduce perceived risk
   - Focus on safety and security
   - Low-pressure approach
   - Example tone: "You can try this risk-free. Many businesses like yours have seen results."

2) VALUE-BASED VERSION:
   - Lead with clear value proposition
   - Quantify benefits when possible
   - Focus on ROI and outcomes
   - Use specific numbers and metrics
   - Example tone: "Save 10 hours per week. Increase revenue by 25%. Here's how."

3) PROOF-DRIVEN VERSION:
   - Start with evidence, testimonials, or data
   - Use social proof and credibility markers
   - Include specific examples or case studies
   - Show, don't just tell
   - Example tone: "Over 500 companies use this. Here's what they achieved: [specific results]"

4) EMOTIONAL VERSION:
   - Connect with user's pain points and desires
   - Use emotional language (but authentic, not manipulative)
   - Tell a story or paint a picture
   - Focus on transformation and outcomes
   - Example tone: "Imagine finally having time for what matters. No more late nights. No more stress."

5) HIGH-CONVERSION DIRECT VERSION:
   - Clear, direct, action-oriented
   - Strong CTA with low friction
   - Benefit-focused headlines
   - Remove all fluff
   - Example tone: "Get [specific benefit] in [timeframe]. Start here."

CTA OPTIMIZATION:
- Create a clear, compelling call-to-action
- Match CTA to audience state (cold = low commitment, warm = higher commitment)
- Use action verbs
- Reduce friction (e.g., "Try free" vs "Buy now")
- Make it specific and time-bound when appropriate

OUTPUT FORMAT:
You MUST return a SINGLE JSON object with this exact schema:

{
  "soft_version": "string",
  "value_version": "string",
  "proof_version": "string",
  "emotional_version": "string",
  "direct_version": "string",
  "cta": "string"
}

CRITICAL:
- Return ONLY valid JSON
- No markdown formatting
- No prose outside JSON
- All fields must be present
- Each version should be a complete, rewritten version of the input text
- CTA should be optimized for the platform, goal, and audience
- Use English unless language is specified otherwise
"""


# ====================================================
# MAIN REWRITE FUNCTION
# ====================================================

async def rewrite_text(input: RewriteInput) -> dict:
    """
    Rewrite marketing text into 5 different professional versions.
    
    This function:
    1. Constructs a user message with text and context
    2. Calls OpenAI API with the rewrite system prompt
    3. Parses and validates the JSON response
    4. Returns structured RewriteOutput
    
    Args:
        input: RewriteInput with text, platform, goal, audience, language
    
    Returns:
        dict with 5 rewritten versions and optimized CTA
    
    Raises:
        ValueError: If API key is missing or response parsing fails
        Exception: For other API or parsing errors
    """
    client = get_client()
    
    # Build user message
    user_message = json.dumps({
        "text": input.text,
        "platform": input.platform,
        "goal": input.goal,
        "audience": input.audience,
        "language": input.language,
    })
    
    # Call OpenAI API
    try:
        messages = [
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content
        
        # Parse JSON safely
        try:
            from json_utils import safe_parse_json
            data = safe_parse_json(raw_content, context="rewrite analysis")
            
            # Ensure all required fields exist with defaults
            required_fields = {
                "soft_version": input.text,  # Fallback to original
                "value_version": input.text,
                "proof_version": input.text,
                "emotional_version": input.text,
                "direct_version": input.text,
                "cta": "Get started"
            }
            
            for key, default_value in required_fields.items():
                if key not in data:
                    data[key] = default_value
            
            return data
            
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: return original text in all versions
            print(f"⚠️ JSON parsing error in rewrite analysis: {str(e)}")
            print(f"⚠️ Raw response preview: {raw_content[:500]}")
            return {
                "soft_version": input.text,
                "value_version": input.text,
                "proof_version": input.text,
                "emotional_version": input.text,
                "direct_version": input.text,
                "cta": "Get started"
            }
    
    except Exception as e:
        print(f"❌ Error in rewrite_text: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
        # Return safe fallback
        return {
            "soft_version": input.text,
            "value_version": input.text,
            "proof_version": input.text,
            "emotional_version": input.text,
            "direct_version": input.text,
            "cta": "Get started"
        }

