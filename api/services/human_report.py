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


async def render_human_report(analysis_json: Dict[str, Any]) -> str:
    """
    Generate human-readable report from analysis JSON.
    
    Args:
        analysis_json: Complete analysis JSON with findings
        
    Returns:
        Human-readable report text
        
    Raises:
        RuntimeError: If OpenAI API key is not available
    """
    # Check if API key is available
    if not OPENAI_API_KEY:
        raise RuntimeError("LLM_UNAVAILABLE")
    
    # Use OpenAI SDK
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        user_prompt = f"""زبان: فارسی
هدف صفحه: {analysis_json.get("input", {}).get("goal")}
URL: {analysis_json.get("input", {}).get("url")}

JSON:
```json
{json.dumps(analysis_json, ensure_ascii=False, indent=2)}
```

{PROMPT_FA}

گزارش را به فارسی بنویس و از اعداد و درصدها استفاده نکن."""
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": PROMPT_FA
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content or "گزارش تولید نشد."
        
    except Exception as e:
        # Re-raise the exception to be handled by the route
        raise RuntimeError(f"LLM_ERROR: {str(e)}") from e

