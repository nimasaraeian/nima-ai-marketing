"""
Fresh OpenAI API test - Python version
"""
import sys
import io
import os
from pathlib import Path
from dotenv import load_dotenv
import openai

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load .env - try multiple methods
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

api_key = None

# Method 1: Try load_dotenv
if env_file.exists():
    load_dotenv(env_file, override=True)
    api_key = os.getenv("OPENAI_API_KEY")

# Method 2: If not found, read directly from file
if not api_key and env_file.exists():
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('OPENAI_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
                    # Remove quotes if present
                    if api_key.startswith('"') and api_key.endswith('"'):
                        api_key = api_key[1:-1]
                    elif api_key.startswith("'") and api_key.endswith("'"):
                        api_key = api_key[1:-1]
                    break
    except Exception as e:
        print(f"[WARNING] Could not read .env file: {e}")

# Method 3: Check environment variable
if not api_key:
    api_key = os.getenv("OPENAI_API_KEY")

print("=" * 60)
print("FRESH OPENAI API TEST")
print("=" * 60)
print()

if not api_key:
    print("[ERROR] OPENAI_API_KEY not found in .env")
    sys.exit(1)

if not api_key.startswith("sk-"):
    print(f"[ERROR] API key doesn't start with 'sk-': {api_key[:10]}...")
    sys.exit(1)

print(f"[OK] API Key found: {api_key[:25]}...{api_key[-15:]}")
print()

# Create client
client = openai.OpenAI(api_key=api_key)

print("Testing API connection...")
print("-" * 60)

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "Say OK if API is working."}
        ],
        max_tokens=10
    )
    
    output = response.choices[0].message.content
    print()
    print("=" * 60)
    print("[SUCCESS] API OK!")
    print("=" * 60)
    print(f"Response: {output}")
    print()
    
except openai.RateLimitError as e:
    print()
    print("=" * 60)
    print("[ERROR] RATE LIMIT / QUOTA ERROR")
    print("=" * 60)
    print(f"Error: {e}")
    print()
    print("Possible causes:")
    print("  - Quota exceeded")
    print("  - Rate limit reached")
    print("  - API key not activated")
    print()
    
except openai.AuthenticationError as e:
    print()
    print("=" * 60)
    print("[ERROR] AUTHENTICATION ERROR")
    print("=" * 60)
    print(f"Error: {e}")
    print()
    print("Check:")
    print("  - API key is correct")
    print("  - API key is active")
    print()
    
except Exception as e:
    print()
    print("=" * 60)
    print("[ERROR] UNEXPECTED ERROR")
    print("=" * 60)
    print(f"Error Type: {type(e).__name__}")
    print(f"Error: {e}")
    print()

print("=" * 60)


