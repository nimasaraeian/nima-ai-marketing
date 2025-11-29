"""
Test script to use chat.py directly (without API server)
"""
import os
import sys

# Check if OPENAI_API_KEY is set
if not os.getenv("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY environment variable not set.")
    print("Please set it before running:")
    print("  $env:OPENAI_API_KEY='your-api-key'")
    sys.exit(1)

try:
    from chat import chat_completion
    
    message = "یک مقاله ۷ بخشی برای AI Marketing 2026 بنویس. فقط مراحل کار را بده، نه متن مقاله را."
    
    print("=" * 60)
    print("AI BRAIN RESPONSE")
    print("=" * 60)
    print()
    print("Sending request...")
    print()
    
    response = chat_completion(message)
    
    print(response)
    print()
    print("=" * 60)
    
except ValueError as e:
    print(f"ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)





