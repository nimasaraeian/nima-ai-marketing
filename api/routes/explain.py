"""
OpenAI-powered explanation endpoint for decision diagnosis.

This endpoint takes a diagnosis response (from /analyze-url or similar)
and generates client-ready explanations without modifying the diagnosis.
"""

import json
import logging
import os
from typing import Dict, Any, List, Literal, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pathlib import Path

# Import OpenAI client - use direct initialization to ensure env vars are loaded
from openai import OpenAI

router = APIRouter()
logger = logging.getLogger("explain")

# Load environment variables
# Use the same loading strategy as main.py
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
else:
    # Fallback to api/.env if it exists
    api_env = Path(__file__).parent.parent / ".env"
    if api_env.exists():
        load_dotenv(api_env, override=True)
    else:
        load_dotenv()  # Load from current directory or system env


class ExplainRequest(BaseModel):
    """Request model for explanation endpoint."""
    diagnosis: Dict[str, Any] = Field(..., description="Diagnosis response from /analyze-url or subset")
    audience: Literal["ceo", "marketer", "ux"] = Field(default="marketer", description="Target audience for explanation")
    language: Literal["en", "fa"] = Field(default="en", description="Output language")


class TopAction(BaseModel):
    """A single top action recommendation."""
    title: str = Field(..., description="Short action title")
    why: str = Field(..., description="Why this action matters")
    how: str = Field(..., description="How to implement")
    example_copy: str = Field(..., description="Example copy/text to use")


class ExplainResponse(BaseModel):
    """Response model for explanation endpoint."""
    analysisStatus: Literal["ok", "error"] = Field(..., description="Status of the explanation")
    summary: str = Field(..., description="6-8 lines client-ready summary")
    why_users_hesitate: str = Field(..., description="2-4 sentences explaining why users hesitate")
    top_actions: List[TopAction] = Field(..., description="Top actionable recommendations")
    risk_reversal_copy: str = Field(..., description="Short guarantee/reassurance text")
    disclaimer: str = Field(..., description="Disclaimer about validation")


def _extract_diagnosis_data(diagnosis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract compact subset of diagnosis data for prompt building.
    
    Returns:
        Dict with: brain scores, blockers, quick wins, visual trust, key lines
    """
    extracted = {}
    
    # Brain scores
    brain = diagnosis.get("brain", {})
    if isinstance(brain, dict):
        extracted["brain"] = {
            "frictionScore": brain.get("frictionScore"),
            "trustScore": brain.get("trustScore"),
            "clarityScore": brain.get("clarityScore"),
            "decisionProbability": brain.get("decisionProbability"),
            "confidence": brain.get("confidence"),
        }
        
        # Key decision blockers
        blockers = brain.get("keyDecisionBlockers", [])
        if blockers:
            extracted["brain"]["keyDecisionBlockers"] = []
            for blocker in blockers[:5]:  # Top 5 only
                if isinstance(blocker, dict):
                    extracted["brain"]["keyDecisionBlockers"].append({
                        "name": blocker.get("name"),
                        "severity": blocker.get("severity"),
                        "evidence": blocker.get("evidence"),
                        "fix": blocker.get("fix"),
                    })
        
        # Recommended quick wins
        quick_wins = brain.get("recommendedQuickWins", [])
        if quick_wins:
            extracted["brain"]["recommendedQuickWins"] = quick_wins[:5]  # Top 5 only
    
    # Visual trust
    visual_trust = diagnosis.get("visualTrust", {})
    if isinstance(visual_trust, dict):
        extracted["visualTrust"] = {
            "label": visual_trust.get("label"),
            "confidence": visual_trust.get("confidence"),
            "narrative": visual_trust.get("narrative", [])[:3],  # Top 3 narrative items
        }
    
    # Text features - key lines
    features = diagnosis.get("features", {})
    if isinstance(features, dict):
        text_features = features.get("text", {})
        if isinstance(text_features, dict):
            key_lines = text_features.get("key_lines", [])
            if key_lines:
                extracted["features"] = {
                    "text": {
                        "key_lines": key_lines[:5]  # Top 5 key lines
                    }
                }
    
    return extracted


def _build_explanation_prompt(
    diagnosis_data: Dict[str, Any],
    audience: str,
    language: str
) -> str:
    """Build the prompt for OpenAI to generate explanations."""
    
    # Format diagnosis data as JSON string for the prompt
    diagnosis_json = json.dumps(diagnosis_data, indent=2, ensure_ascii=False)
    
    audience_context = {
        "ceo": "executive-level, strategic, business impact focused",
        "marketer": "marketing professional, conversion-focused, actionable",
        "ux": "UX designer, user experience focused, design-oriented"
    }.get(audience, "marketer")
    
    lang_instruction = "Persian (Farsi)" if language == "fa" else "English"
    
    prompt = f"""You are an expert conversion optimization consultant explaining a decision diagnosis analysis.

CRITICAL RULE: You must NOT change or modify the diagnosis. You can ONLY explain what is already provided.

The diagnosis data is:
{diagnosis_json}

Your task is to explain this diagnosis in a clear, actionable way for a {audience_context} audience.
Write in {lang_instruction}.

Generate a JSON response with this exact structure:
{{
  "summary": "6-8 lines client-ready summary explaining the overall diagnosis",
  "why_users_hesitate": "2-4 sentences explaining why users hesitate based on the diagnosis",
  "top_actions": [
    {{
      "title": "Short action title",
      "why": "Why this action matters",
      "how": "How to implement this action",
      "example_copy": "Example copy/text to use"
    }}
  ],
  "risk_reversal_copy": "Short guarantee/reassurance text based on the diagnosis",
  "disclaimer": "Based on detected signals; validate with analytics."
}}

Requirements:
- summary: 6-8 lines, client-ready, no technical jargon
- why_users_hesitate: 2-4 sentences, based on the diagnosis data
- top_actions: 3-5 actions, prioritized by impact
- risk_reversal_copy: Short, compelling guarantee/reassurance text
- disclaimer: Standard disclaimer about validation

Return ONLY valid JSON. No markdown, no code blocks, no explanations outside the JSON."""
    
    return prompt


async def _generate_explanation(
    diagnosis_data: Dict[str, Any],
    audience: str,
    language: str
) -> Dict[str, Any]:
    """Generate explanation using OpenAI."""
    
    # Ensure .env is loaded (same strategy as api/main.py)
    # api/main.py uses: Path(__file__).parent.parent (2 levels up from api/main.py)
    # api/routes/explain.py needs: Path(__file__).parent.parent.parent (3 levels up)
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
    else:
        # Fallback to api/.env if it exists
        api_env = Path(__file__).parent.parent / ".env"
        if api_env.exists():
            load_dotenv(api_env, override=True)
        else:
            load_dotenv()  # Load from current directory or system env
    
    # Also try loading from current working directory (in case __file__ path is different at runtime)
    import os as os_module
    cwd = os_module.getcwd()
    env_in_cwd = Path(cwd) / ".env"
    if env_in_cwd.exists() and env_in_cwd != env_file:
        load_dotenv(env_in_cwd, override=True)
    
    # Check for API key (using same method as cognitive_friction_engine)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Try reading directly from .env file (same as cognitive_friction_engine.py)
        project_root = Path(__file__).parent.parent.parent
        env_file = project_root / ".env"
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
                                    # Set in environment for future use
                                    os.environ['OPENAI_API_KEY'] = api_key
                                    break
            except Exception as e:
                import logging
                logger = logging.getLogger("explain")
                logger.warning(f"Failed to read OPENAI_API_KEY from .env: {e}")
    
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY environment variable is not set. Please configure it in your .env file."
        )
    
    # Get model from env with default
    model = os.getenv("OPENAI_EXPLAIN_MODEL", "gpt-4o-mini")
    
    # Initialize OpenAI client directly (ensuring env vars are loaded)
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY environment variable is not set. Please configure it in your .env file."
        )
    
    try:
        client = OpenAI(api_key=api_key, timeout=300.0, max_retries=3)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize OpenAI client: {str(e)}"
        )
    
    # Build prompt
    prompt = _build_explanation_prompt(diagnosis_data, audience, language)
    
    try:
        # Call OpenAI API (run in thread pool since OpenAI SDK is synchronous)
        import asyncio
        loop = asyncio.get_event_loop()
        
        def _call_openai():
            return client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a conversion optimization consultant. You explain diagnoses clearly and actionably. Always return valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Low temperature for consistent explanations
                response_format={"type": "json_object"}  # Force JSON response
            )
        
        # Run in executor to avoid blocking
        if hasattr(asyncio, 'to_thread'):
            response = await asyncio.to_thread(_call_openai)
        else:
            # Python < 3.9 fallback
            response = await loop.run_in_executor(None, _call_openai)
        
        # Parse response
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")
        
        # Parse JSON
        explanation = json.loads(content)
        
        # Validate structure
        if not isinstance(explanation, dict):
            raise ValueError("Response is not a JSON object")
        
        # Ensure all required fields exist
        result = {
            "analysisStatus": "ok",
            "summary": explanation.get("summary", "Summary not available."),
            "why_users_hesitate": explanation.get("why_users_hesitate", "Analysis not available."),
            "top_actions": [],
            "risk_reversal_copy": explanation.get("risk_reversal_copy", "Risk reversal copy not available."),
            "disclaimer": explanation.get("disclaimer", "Based on detected signals; validate with analytics.")
        }
        
        # Parse top_actions
        top_actions_raw = explanation.get("top_actions", [])
        if isinstance(top_actions_raw, list):
            for action in top_actions_raw:
                if isinstance(action, dict):
                    result["top_actions"].append({
                        "title": action.get("title", "Action"),
                        "why": action.get("why", ""),
                        "how": action.get("how", ""),
                        "example_copy": action.get("example_copy", "")
                    })
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OpenAI JSON response: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse explanation response: {str(e)}"
        )
    except Exception as e:
        logger.error(f"OpenAI API error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate explanation: {str(e)}"
        )


@router.post("/explain", response_model=ExplainResponse)
async def explain_endpoint(request: ExplainRequest):
    """
    Generate OpenAI-powered explanation of a decision diagnosis.
    
    Takes a diagnosis response (from /analyze-url or similar) and generates
    client-ready explanations without modifying the diagnosis.
    
    - **diagnosis**: The diagnosis response object (or subset)
    - **audience**: Target audience (ceo, marketer, ux) - default: marketer
    - **language**: Output language (en, fa) - default: en
    
    Returns structured explanation with summary, why users hesitate,
    top actions, risk reversal copy, and disclaimer.
    """
    try:
        # Extract compact diagnosis data
        diagnosis_data = _extract_diagnosis_data(request.diagnosis)
        
        # Generate explanation
        explanation = await _generate_explanation(
            diagnosis_data,
            request.audience,
            request.language
        )
        
        return ExplainResponse(**explanation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in explain endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

