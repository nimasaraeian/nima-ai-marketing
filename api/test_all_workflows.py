"""
Automated test suite for AI Brain operational tests
Tests all 3 workflow types: Task Breakdown, Strategy, and Quality Engine
"""
import requests
import json
import time
import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

API_URL = "http://localhost:8000/chat"

def test_api_connection():
    """Check if API server is running"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

def run_test(test_name, message, test_number):
    """Run a single test and return the response"""
    print("\n" + "=" * 60)
    print(f"TEST {test_number} — {test_name}")
    print("=" * 60)
    print(f"\nRequest: {message[:80]}...")
    print("\nSending request...\n")
    
    payload = {
        "message": message,
        "model": "gpt-4",
        "temperature": 0.7
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return result["response"]
        
    except requests.exceptions.ConnectionError:
        return "ERROR: Could not connect to API server. Make sure server is running."
    except requests.exceptions.Timeout:
        return "ERROR: Request timed out."
    except Exception as e:
        return f"ERROR: {str(e)}"

def main():
    print("=" * 60)
    print("AI BRAIN OPERATIONAL TESTS")
    print("=" * 60)
    print("\nChecking API connection...")
    
    if not test_api_connection():
        print("❌ ERROR: API server is not running!")
        print("\nPlease start the server first:")
        print("  python -m uvicorn api.app:app --host localhost --port 8000")
        sys.exit(1)
    
    print("✅ API server is running\n")
    
    # Test 1: Task Breakdown Workflow
    test1_message = "یک مقاله ۷ بخشی برای AI Marketing 2026 بنویس. فقط مراحل کار را بده، نه متن مقاله را."
    test1_result = run_test("TASK BREAKDOWN WORKFLOW", test1_message, 1)
    
    print("\n" + "=" * 60)
    print("TEST 1 RESULT")
    print("=" * 60)
    print()
    print(test1_result)
    print()
    
    # Wait a bit between tests
    time.sleep(2)
    
    # Test 2: Strategy Workflow
    test2_message = "برای یک کلینیک زیبایی در استانبول یک استراتژی ۳۰ روزه AI Marketing بنویس. لطفاً از مدل Strategy Workflow استفاده کن."
    test2_result = run_test("STRATEGY WORKFLOW", test2_message, 2)
    
    print("\n" + "=" * 60)
    print("TEST 2 RESULT")
    print("=" * 60)
    print()
    print(test2_result)
    print()
    
    # Wait a bit between tests
    time.sleep(2)
    
    # Test 3: Quality Engine Test
    test3_message = "در مورد CRM یک متن حرفه‌ای و عمیق بنویس اما هیچ تعریف ابتدایی از CRM نده."
    test3_result = run_test("QUALITY ENGINE TEST", test3_message, 3)
    
    print("\n" + "=" * 60)
    print("TEST 3 RESULT")
    print("=" * 60)
    print()
    print(test3_result)
    print()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("\n✅ All 3 tests completed")
    print("\nTests performed:")
    print("  1. Task Breakdown Workflow (WRITING_WORKFLOW)")
    print("  2. Strategy Workflow (STRATEGY_WORKFLOW)")
    print("  3. Quality Engine Test (Depth & Relevance)")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()





