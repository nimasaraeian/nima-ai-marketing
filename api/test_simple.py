"""
Simple test to check if API works and see response quality
"""
import os
import sys
import io
from pathlib import Path

# Fix encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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

try:
    from chat import chat_completion
    
    # Simple test message
    test_message = """یک کلینیک زیبایی در استانبول با بودجه 3000 دلار در ماه Meta ads اجرا می‌کند.
ROAS: 1.2، CPC: 2.5 دلار، Conversion rate: 1%

یک تحلیل کوتاه بده با:
- مثال‌های مشخص از ad headlines
- پیشنهادات محلی برای استانبول
- اقدامات مشخص (نه "بهبود تبلیغات")"""
    
    print("=" * 60)
    print("TEST: Simple Marketing Analysis")
    print("=" * 60)
    print()
    print("Request:")
    print("-" * 60)
    print(test_message)
    print()
    print("Processing...")
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
    
    # Check for required elements
    print("Quality Check:")
    print("-" * 60)
    has_headline = "Headline" in response or "headline" in response.lower()
    has_example = "Example" in response or "مثال" in response
    has_istanbul = "Istanbul" in response or "استانبول" in response
    has_tourist = "tourist" in response.lower() or "گردشگر" in response
    has_specific = any(word in response.lower() for word in ["create", "test", "build", "ساخت", "ایجاد"])
    
    print(f"  {'✓' if has_headline else '✗'} Headline examples")
    print(f"  {'✓' if has_example else '✗'} Concrete examples")
    print(f"  {'✓' if has_istanbul else '✗'} Istanbul context")
    print(f"  {'✓' if has_tourist else '✗'} Tourist/local context")
    print(f"  {'✓' if has_specific else '✗'} Specific actions")
    print("=" * 60)
    
except ValueError as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)




