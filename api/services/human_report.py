"""
Generate human-readable report from analysis JSON using OpenAI.
"""
import os
import json
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

PROMPT_FA = """تو یک Conversion & Decision UX Auditor هستی.

از عدد، نمره، درصد، confidence و واژه‌های فنی بی‌مصرف استفاده نکن.

فقط مشکل‌های قابل اقدام. اگر شواهد کافی نیست، صادقانه بگو «شواهد کافی نیست».

خروجی باید شامل: 3 مشکل اصلی + 5 Quick Wins + پیشنهاد متن (Headline/CTA) + چک‌لیست اجرا.
"""

PROMPT_EN = """You are a Conversion & Decision UX Auditor.

Do not use numbers, scores, percentages, confidence, or unnecessary technical jargon.

Only actionable problems. If there is insufficient evidence, honestly say "insufficient evidence".

Output must include: 3 main issues + 5 Quick Wins + suggested copy (Headline/CTA) + implementation checklist.
"""


async def render_human_report(analysis_json: Dict[str, Any], locale: str = "en") -> str:
    """
    Generate human-readable report from analysis JSON.
    
    Args:
        analysis_json: Complete analysis JSON with findings
        locale: Language locale (fa, en, tr). Default: en (English)
        
    Returns:
        Human-readable report text
        
    Raises:
        RuntimeError: If OpenAI API key is not available
    """
    # Check if API key is available
    if not OPENAI_API_KEY:
        raise RuntimeError("LLM_UNAVAILABLE")
    
    # Determine language and prompt
    is_persian = locale and locale.lower() == "fa"
    prompt = PROMPT_FA if is_persian else PROMPT_EN
    language_name = "فارسی" if is_persian else "English"
    language_instruction = "گزارش را به فارسی بنویس و از اعداد و درصدها استفاده نکن." if is_persian else "Write the report in English and do not use numbers or percentages."
    error_message = "گزارش تولید نشد." if is_persian else "Report generation failed."
    
    # Use OpenAI SDK
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        user_prompt = f"""Language: {language_name}
Page Goal: {analysis_json.get("input", {}).get("goal")}
URL: {analysis_json.get("input", {}).get("url")}

JSON:
```json
{json.dumps(analysis_json, ensure_ascii=False, indent=2)}
```

{prompt}

{language_instruction}"""
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content or error_message
        
    except Exception as e:
        # Re-raise the exception to be handled by the route
        raise RuntimeError(f"LLM_ERROR: {str(e)}") from e

