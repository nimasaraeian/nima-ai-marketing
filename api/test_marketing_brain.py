"""
Test script to verify NIMA MARKETING BRAIN integration
"""
import requests
import json
import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

API_URL = "http://localhost:8000/chat"

def test_marketing_brain():
    """Test the marketing brain with a real marketing scenario"""
    
    # Test message that should trigger marketing brain logic
    test_message = """یک رستوران در استانبول می‌خواهد با بودجه 5000 دلار در ماه تبلیغ کند. 
Meta ads اجرا کرده اما CTR پایین است (0.5%) و هیچ رزروی نمی‌گیرد. 
یک تحلیل کامل بده و راهکار پیشنهاد کن."""
    
    payload = {
        "message": test_message,
        "model": "gpt-4",
        "temperature": 0.7
    }
    
    print("=" * 60)
    print("TEST: NIMA MARKETING BRAIN")
    print("=" * 60)
    print()
    print("Request:")
    print("-" * 60)
    print(test_message)
    print()
    print("Sending request to API...")
    print()
    
    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        print("=" * 60)
        print("RESPONSE")
        print("=" * 60)
        print()
        print(result["response"])
        print()
        print("=" * 60)
        print()
        print("✅ Test completed successfully!")
        print()
        print("Expected: Response should show:")
        print("  - Diagnostic sequence (6 steps)")
        print("  - Campaign performance diagnosis")
        print("  - 4P analysis")
        print("  - Strategic priorities (Budget, Market Pull, Competition)")
        print("  - Realistic recommendations")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to API server.")
        print("Make sure the server is running:")
        print("  python -m uvicorn api.app:app --host localhost --port 8000")
    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timed out.")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_marketing_brain()




