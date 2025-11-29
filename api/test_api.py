"""
API connectivity test - Safe ping test
"""
import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import openai
import os
from pathlib import Path

# Load API key from .env
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
    print("[ERROR] ERROR: OPENAI_API_KEY not found")
    print("   Check .env file in project root")
    exit(1)

print("=" * 60)
print("API CONNECTIVITY TEST")
print("=" * 60)
print()
print(f"API Key: {api_key[:20]}...{api_key[-10:]}")
print()

client = openai.OpenAI(api_key=api_key)

try:
    print("Testing API connection...")
    print()
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "Ping test: return OK if API works."}
        ],
        max_tokens=10
    )
    
    output_text = response.choices[0].message.content
    print("=" * 60)
    print("[OK] API WORKING")
    print("=" * 60)
    print(f"Response: {output_text}")
    print()
    print("API is ready for use!")
    print("=" * 60)
    
except openai.RateLimitError as e:
    print("=" * 60)
    print("[ERROR] RATE LIMIT ERROR")
    print("=" * 60)
    print(f"Error Type: RateLimitError")
    print(f"Details: {e}")
    print()
    print("Possible causes:")
    print("  - Quota exceeded")
    print("  - Too many requests")
    print("  - Rate limit reached")
    print()
    if hasattr(e, 'response') and e.response:
        print("Rate limit details:")
        print(f"  Status: {e.response.status_code}")
        if hasattr(e.response, 'headers'):
            print(f"  Headers: {e.response.headers}")
    print("=" * 60)
    
except openai.APIError as e:
    print("=" * 60)
    print("[ERROR] API ERROR")
    print("=" * 60)
    print(f"Error Type: APIError")
    print(f"Details: {e}")
    print()
    if hasattr(e, 'status_code'):
        print(f"Status Code: {e.status_code}")
    if hasattr(e, 'response'):
        print(f"Response: {e.response}")
    print("=" * 60)
    
except Exception as e:
    print("=" * 60)
    print("[ERROR] ERROR")
    print("=" * 60)
    print(f"Error Type: {type(e).__name__}")
    print(f"Details: {e}")
    print()
    import traceback
    print("Full traceback:")
    traceback.print_exc()
    print("=" * 60)

