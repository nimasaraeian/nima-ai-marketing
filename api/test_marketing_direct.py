"""
Direct test of marketing brain (without API server)
"""
import os
import sys
import io

# Fix encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Check API key
from pathlib import Path

# Try to load from .env file directly
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

api_key_loaded = False
if env_file.exists():
    print("📄 Loading API key from .env file...")
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
            for line in content.splitlines():
                line = line.strip()
                if line.startswith('OPENAI_API_KEY='):
                    api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                    os.environ['OPENAI_API_KEY'] = api_key
                    print("✅ API key loaded from .env")
                    api_key_loaded = True
                    break
    except Exception as e:
        print(f"⚠️  Error reading .env: {e}")
    
    if not api_key_loaded:
        # Try dotenv as fallback
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            if os.getenv("OPENAI_API_KEY"):
                api_key_loaded = True
                print("✅ API key loaded via dotenv")
        except Exception as e:
            print(f"⚠️  Error with dotenv: {e}")
else:
    print("⚠️  .env file not found, trying environment variable...")
    from dotenv import load_dotenv
    load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("❌ ERROR: OPENAI_API_KEY not found")
    print(f"   Checked: {env_file}")
    sys.exit(1)

try:
    from chat import chat_completion
    
    test_message = """یک رستوران در استانبول می‌خواهد با بودجه 5000 دلار در ماه تبلیغ کند. 
Meta ads اجرا کرده اما CTR پایین است (0.5%) و هیچ رزروی نمی‌گیرد. 
یک تحلیل کامل بده و راهکار پیشنهاد کن."""
    
    print("=" * 60)
    print("TEST: NIMA MARKETING BRAIN")
    print("=" * 60)
    print()
    print("Request:")
    print("-" * 60)
    print(test_message)
    print()
    print("Processing with AI Brain (this may take 30-60 seconds)...")
    print()
    
    response = chat_completion(test_message, model="gpt-4", temperature=0.7)
    
    print("=" * 60)
    print("RESPONSE")
    print("=" * 60)
    print()
    print(response)
    print()
    print("=" * 60)
    print()
    print("✅ Test completed!")
    print()
    print("Expected elements in response:")
    print("  ✓ Diagnostic sequence (Business, Digital Presence, etc.)")
    print("  ✓ Campaign performance diagnosis (CTR, conversion issues)")
    print("  ✓ 4P analysis (Product, Price, Place, Promotion)")
    print("  ✓ Strategic priorities (Budget, Market Pull, Competition)")
    print("  ✓ Realistic recommendations with risks")
    print("=" * 60)
    
except ValueError as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

