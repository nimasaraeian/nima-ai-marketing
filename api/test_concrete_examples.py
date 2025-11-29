"""
Test to verify concrete examples and localization are being used
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

from chat import chat_completion

# Test message that should trigger concrete examples and localization
test_message = """یک رستوران در استانبول می‌خواهد با بودجه 5000 دلار در ماه تبلیغ کند. 
Meta ads اجرا کرده اما CTR پایین است (0.5%) و هیچ رزروی نمی‌گیرد.

لطفاً از Response Blueprint استفاده کن و:
1. Snapshot بده
2. Root-Cause Analysis با مثال‌های مشخص
3. 4P Scan با مثال‌های مشخص از ad hooks و headlines
4. Action Plan با اقدامات مشخص (نه "بهبود تبلیغات")
5. Metrics & Targets
6. Risk & Reality Check

مهم: حتماً مثال‌های مشخص از ad copy و headlines برای استانبول بده."""

print("=" * 60)
print("TEST: Concrete Examples & Localization")
print("=" * 60)
print()
print("Request:")
print("-" * 60)
print(test_message)
print()
print("Processing... (this may take 30-60 seconds)")
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
print("Checking for required elements:")
print("-" * 60)

# Check for concrete examples
has_headline = "Headline" in response or "headline" in response.lower()
has_ad_copy = "ad copy" in response.lower() or "Ad copy" in response
has_istanbul = "Istanbul" in response or "استانبول" in response
has_tourist = "tourist" in response.lower() or "گردشگر" in response
has_specific_action = any(word in response.lower() for word in ["create", "test", "implement", "build", "ساخت", "ایجاد", "تست"])

print(f"  {'✓' if has_headline else '✗'} Headline examples")
print(f"  {'✓' if has_ad_copy else '✗'} Ad copy examples")
print(f"  {'✓' if has_istanbul else '✗'} Istanbul context")
print(f"  {'✓' if has_tourist else '✗'} Tourist/local context")
print(f"  {'✓' if has_specific_action else '✗'} Specific actions")
print("=" * 60)




