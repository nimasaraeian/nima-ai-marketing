"""
Detailed API test with different models and error analysis
"""
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import openai
import os
from pathlib import Path
import time

# Load API key
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('OPENAI_API_KEY='):
                api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                os.environ['OPENAI_API_KEY'] = api_key
                break

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("[ERROR] OPENAI_API_KEY not found")
    exit(1)

print("=" * 60)
print("DETAILED API TEST")
print("=" * 60)
print()
print(f"API Key: {api_key[:25]}...{api_key[-15:]}")
print()

client = openai.OpenAI(api_key=api_key)

# Test with different models
models_to_test = [
    ("gpt-4o-mini", "Cheapest option"),
    ("gpt-3.5-turbo", "Fast option"),
]

for model_name, description in models_to_test:
    print(f"Testing {model_name} ({description})...")
    print("-" * 60)
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": "Say OK"}
            ],
            max_tokens=5
        )
        
        output = response.choices[0].message.content
        print(f"[OK] {model_name} works!")
        print(f"Response: {output}")
        print()
        break  # If one works, we're good
        
    except openai.RateLimitError as e:
        print(f"[ERROR] RateLimitError for {model_name}")
        error_detail = str(e)
        if "insufficient_quota" in error_detail:
            print("  -> Quota issue (not rate limit)")
        elif "rate_limit" in error_detail.lower():
            print("  -> Rate limit (too many requests)")
        print()
        time.sleep(2)  # Wait before next test
        
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        print()
        time.sleep(2)

print("=" * 60)
print("Test complete")
print("=" * 60)




