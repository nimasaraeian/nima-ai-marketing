"""
Generate human-readable report from analysis JSON using OpenAI.
ENGLISH ONLY - All output must be in English. Persian/Farsi is forbidden.
"""
import os
import json
import re
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Load .env from project root (same as main.py)
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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Persian/Farsi Unicode range: \u0600-\u06FF
PERSIAN_UNICODE_RANGE = re.compile(r'[\u0600-\u06FF]')

PROMPT_EN = """You are a Conversion & Decision UX Auditor.

CRITICAL LANGUAGE RULE: You MUST write ONLY in English. Persian, Farsi, Arabic, or any non-English language is FORBIDDEN.

SPECIFICITY REQUIREMENTS:

1. QUOTE ACTUAL PAGE ELEMENTS:
   - Always quote the detected H1 headline exactly as it appears on the page (use quotes: "H1 text here")
   - Always quote the top 2 CTA labels exactly as they appear (use quotes: "CTA text here")
   - Reference specific elements found in page_map.headlines and page_map.ctas

2. LOCATION SPECIFICITY:
   - For each issue, specify if it's "Above-the-Fold" or "Below-the-Fold"
   - Use the capture.viewport information to determine fold position
   - If an issue relates to the H1 or primary CTA, it's likely Above-the-Fold
   - If an issue relates to secondary CTAs or lower content, it's likely Below-the-Fold

3. PAGE-SPECIFIC RECOMMENDATIONS:
   - Replace generic advice with specific recommendations referencing actual elements
   - Instead of "improve your headline", say "Change 'Current H1 Text' to [specific suggestion]"
   - Instead of "make CTA clearer", say "Replace 'Current CTA Text' with [specific suggestion]"
   - Reference actual CTA labels and headlines found in the page_map

Do not use numbers, scores, percentages, confidence, or unnecessary technical jargon.

Only actionable problems. If there is insufficient evidence, honestly say "insufficient evidence".

Output must include: 3 main issues + 5 Quick Wins + suggested copy (Headline/CTA) + implementation checklist.

ALL OUTPUT MUST BE IN ENGLISH. Any non-English characters (especially Persian/Farsi Unicode range \\u0600-\\u06FF) will cause the system to fail.
"""


def contains_persian(text: str) -> bool:
    """
    Detect if text contains Persian/Farsi characters (Unicode range \\u0600-\\u06FF).
    
    Args:
        text: Text to check
        
    Returns:
        True if Persian characters are detected, False otherwise
    """
    if not text:
        return False
    return bool(PERSIAN_UNICODE_RANGE.search(text))


def validate_english_only(text: str) -> tuple[bool, str]:
    """
    Validate that text contains only English characters (no Persian/Farsi).
    
    Args:
        text: Text to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        is_valid: True if text is English-only, False if Persian detected
        error_message: Error description if validation fails
    """
    if not text:
        return True, ""
    
    if contains_persian(text):
        # Find the first Persian character for debugging
        match = PERSIAN_UNICODE_RANGE.search(text)
        pos = match.start() if match else 0
        context = text[max(0, pos-20):pos+20]
        return False, f"Persian/Farsi characters detected at position {pos}. Context: {repr(context)}"
    
    return True, ""


async def render_human_report(analysis_json: Dict[str, Any], locale: str = "en") -> str:
    """
    Generate human-readable report from analysis JSON.
    
    CRITICAL: Output is ALWAYS in English, regardless of locale parameter.
    Any Persian/Farsi characters in output will cause a RuntimeError.
    
    Args:
        analysis_json: Complete analysis JSON with findings
        locale: Ignored - output is always English
        
    Returns:
        Human-readable report text in English only
        
    Raises:
        RuntimeError: If OpenAI API key is not available, or if output contains Persian characters
    """
    # Check if API key is available
    if not OPENAI_API_KEY:
        raise RuntimeError("LLM_UNAVAILABLE")
    
    # ALWAYS use English - ignore locale parameter
    # Use OpenAI SDK
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        # Extract key elements for context
        page_map = analysis_json.get("page_map", {})
        headlines = page_map.get("headlines", []) if isinstance(page_map, dict) else []
        ctas = page_map.get("ctas", []) if isinstance(page_map, dict) else []
        capture = analysis_json.get("capture", {})
        viewport = capture.get("viewport", {}) if isinstance(capture, dict) else {}
        
        # Find H1
        h1_text = None
        for h in headlines:
            if isinstance(h, dict) and h.get("tag") == "h1":
                h1_text = h.get("text", "")
                break
        
        # Get top 2 CTAs
        top_ctas = []
        for cta in ctas[:2]:
            if isinstance(cta, dict):
                label = cta.get("label", "") or cta.get("text", "")
                if label:
                    top_ctas.append(label)
        
        # Build context section
        context_lines = []
        if h1_text:
            context_lines.append(f"Detected H1: \"{h1_text}\"")
        if top_ctas:
            for i, cta_label in enumerate(top_ctas, 1):
                context_lines.append(f"Top CTA #{i}: \"{cta_label}\"")
        if viewport:
            viewport_height = viewport.get("height", 900) if isinstance(viewport, dict) else 900
            context_lines.append(f"Viewport: {viewport.get('width', 'unknown')}x{viewport_height} (fold is approximately at {viewport_height}px)")
        
        context_section = "\n".join(context_lines) if context_lines else "No specific elements detected."
        
        user_prompt = f"""Page Goal: {analysis_json.get("input", {}).get("goal")}
URL: {analysis_json.get("input", {}).get("url")}

DETECTED PAGE ELEMENTS:
{context_section}

FULL ANALYSIS DATA:
```json
{json.dumps(analysis_json, ensure_ascii=False, indent=2)}
```

{PROMPT_EN}

CRITICAL: 
- Quote the H1 and top 2 CTAs exactly as shown above
- Specify Above-the-Fold vs Below-the-Fold for each issue
- Make recommendations specific to the actual elements found (not generic advice)

Write the report in English. Do not use numbers or percentages. Any non-English output will be rejected."""
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": PROMPT_EN
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        report_text = response.choices[0].message.content or "Report generation failed."
        
        # CRITICAL: Validate output is English-only
        is_valid, error_msg = validate_english_only(report_text)
        if not is_valid:
            # This is a blocking error - Persian output is forbidden
            raise RuntimeError(f"ENGLISH_ONLY_VIOLATION: Generated report contains Persian/Farsi characters. {error_msg}")
        
        return report_text
        
    except RuntimeError:
        # Re-raise RuntimeError as-is (including our validation errors)
        raise
    except Exception as e:
        # Re-raise the exception to be handled by the route
        raise RuntimeError(f"LLM_ERROR: {str(e)}") from e
