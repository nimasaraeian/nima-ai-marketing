"""
Simple OpenAI test - direct file reading
"""
import sys
import io
from pathlib import Path
import openai

# Fix encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Read .env directly
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

print("=" * 60)
print("SIMPLE OPENAI TEST")
print("=" * 60)
print()

api_key = None

if env_file.exists():
    # Try multiple encodings
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    for encoding in encodings:
        try:
            with open(env_file, 'r', encoding=encoding) as f:
                content = f.read()
                print(f"[DEBUG] Read file with {encoding}, length: {len(content)}")
                for line in content.split('\n'):
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
                                print(f"[DEBUG] Found API key: {api_key[:30]}...")
                                break
                if api_key:
                    break
        except Exception as e:
            print(f"[DEBUG] Failed with {encoding}: {e}")
            continue

if not api_key:
    print("[ERROR] Could not read OPENAI_API_KEY from .env")
    print(f"[DEBUG] File path: {env_file}")
    print(f"[DEBUG] File exists: {env_file.exists()}")
    sys.exit(1)

if not api_key.startswith("sk-"):
    print(f"[ERROR] Invalid API key format: {api_key[:20]}...")
    sys.exit(1)

print(f"[OK] API Key loaded: {api_key[:25]}...{api_key[-15:]}")
print()
print("Testing OpenAI API...")
print("-" * 60)
print()

try:
    client = openai.OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "Say OK if API is working."}
        ],
        max_tokens=10
    )
    
    output = response.choices[0].message.content
    
    print("=" * 60)
    print("[SUCCESS] ✅ OpenAI API کار می‌کند!")
    print("=" * 60)
    print(f"Response: {output}")
    print()
    
except openai.RateLimitError as e:
    print("=" * 60)
    print("[ERROR] ❌ Quota Error (429)")
    print("=" * 60)
    print(f"Error: {str(e)[:200]}")
    print()
    print("مشکل: Quota یا Rate Limit")
    print("راه‌حل: بررسی داشبورد OpenAI")
    print()
    
except openai.AuthenticationError as e:
    print("=" * 60)
    print("[ERROR] ❌ Authentication Error (401)")
    print("=" * 60)
    print(f"Error: {str(e)[:200]}")
    print()
    print("مشکل: API key نامعتبر")
    print()
    
except Exception as e:
    print("=" * 60)
    print(f"[ERROR] ❌ {type(e).__name__}")
    print("=" * 60)
    print(f"Error: {str(e)[:200]}")
    print()

print("=" * 60)

