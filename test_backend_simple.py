"""
Simple backend test script (Windows-compatible)
"""
import requests
import json

BACKEND_URL = "http://127.0.0.1:8000"

def test_endpoint(name, method="GET", url_suffix="", data=None):
    """Test a single endpoint"""
    try:
        url = f"{BACKEND_URL}{url_suffix}"
        if method == "GET":
            response = requests.get(url, timeout=5)
        else:
            response = requests.post(url, json=data, timeout=30)
        
        print(f"\n[{name}]")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            try:
                result = response.json()
                if isinstance(result, dict):
                    print(f"  Response keys: {list(result.keys())[:5]}")
                else:
                    print(f"  Response: {str(result)[:100]}")
                print("  [OK]")
                return True
            except:
                print(f"  Response: {response.text[:100]}")
                print("  [OK]")
                return True
        else:
            print(f"  Error: {response.text[:200]}")
            print("  [FAILED]")
            return False
    except Exception as e:
        print(f"  Error: {str(e)[:100]}")
        print("  [FAILED]")
        return False

def main():
    print("=" * 60)
    print("Backend API Test")
    print("=" * 60)
    
    results = []
    
    # Test 1: Health
    results.append(("Health Check", test_endpoint("Health", "GET", "/health")))
    
    # Test 2: Root
    results.append(("Root Endpoint", test_endpoint("Root", "GET", "/")))
    
    # Test 3: Brain Test
    results.append(("Brain Test", test_endpoint(
        "Brain Test", 
        "POST", 
        "/api/brain/test",
        {"query": "test", "role": "ai_marketing_strategist"}
    )))
    
    # Test 4: Packages
    results.append(("Packages", test_endpoint("Packages", "GET", "/api/packages")))
    
    # Test 5: System Prompt Info
    results.append(("System Prompt Info", test_endpoint("System Info", "GET", "/api/system-prompt/info")))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {name}: {status}")
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)

if __name__ == "__main__":
    main()
























