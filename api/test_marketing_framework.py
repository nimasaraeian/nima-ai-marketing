"""
Test to verify NIMA MARKETING BRAIN framework is being used
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

# Test message that should trigger the diagnostic sequence
test_message = """لطفاً از فریم‌ورک NIMA MARKETING BRAIN استفاده کن و برای این سناریو تحلیل کن:

یک کلینیک زیبایی در استانبول:
- بودجه: 3000 دلار در ماه
- Meta ads اجرا می‌کند اما ROAS فقط 1.2 است
- CPC بالا است (2.5 دلار)
- Conversion rate پایین (1%)

لطفاً:
1. از Core Diagnostic Sequence استفاده کن (6 مرحله)
2. Campaign Performance Diagnosis انجام بده
3. 4P Scan انجام بده
4. Strategic Priorities را مشخص کن (Budget, Market Pull, Competition)"""

print("=" * 60)
print("TEST: NIMA MARKETING BRAIN FRAMEWORK")
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




