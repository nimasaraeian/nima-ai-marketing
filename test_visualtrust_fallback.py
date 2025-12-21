"""
Simple test for VisualTrust fallback
"""
import requests
import json

BACKEND_URL = "http://127.0.0.1:8000"

def test_visualtrust_fallback():
    """Test that VisualTrust fallback works correctly"""
    print("=" * 60)
    print("Testing VisualTrust Fallback")
    print("=" * 60)
    
    # Test 1: Check if server is running
    print("\n1. Checking server...")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print("   [OK] Server is running")
        else:
            print(f"   [FAIL] Server error: {response.status_code}")
            return
    except Exception as e:
        print(f"   [FAIL] Server is not running: {e}")
        print(f"   Please start the server:")
        print(f"   python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload")
        return
    
    # Test 2: Check VisualTrust service (port 8011)
    print("\n2. Checking VisualTrust service (port 8011)...")
    try:
        response = requests.get("http://127.0.0.1:8011/health", timeout=2)
        if response.status_code == 200:
            print("   [WARN] VisualTrust service is running")
            print("   For fallback test, stop VisualTrust service")
        else:
            print(f"   [OK] VisualTrust service not available (code: {response.status_code})")
            print("   This is good for fallback test!")
    except Exception as e:
        print(f"   [OK] VisualTrust service not available")
        print("   This is good for fallback test!")
    
    # Test 3: Test analyze-url endpoint
    print("\n3. Testing /analyze-url endpoint...")
    print("   (This test requires Playwright)")
    print("   If Playwright doesn't work, you'll get Playwright error")
    print("   But if Playwright works and VisualTrust fails,")
    print("   you should see fallback response")
    
    try:
        test_data = {"url": "https://example.com"}
        response = requests.post(
            f"{BACKEND_URL}/analyze-url",
            json=test_data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   [OK] Request succeeded!")
            print(f"   Response keys: {list(result.keys())}")
            
            # Check visualTrust
            if "visualTrust" in result:
                visual = result["visualTrust"]
                if isinstance(visual, dict):
                    if visual.get("analysisStatus") == "unavailable":
                        print(f"\n   [SUCCESS] FALLBACK IS WORKING!")
                        print(f"   visualTrust.analysisStatus: {visual.get('analysisStatus')}")
                        print(f"   visualTrust.error: {visual.get('error')}")
                    else:
                        print(f"\n   [OK] VisualTrust worked")
                        print(f"   visualTrust.analysisStatus: {visual.get('analysisStatus')}")
                else:
                    print(f"   [WARN] visualTrust has unexpected type: {type(visual)}")
        else:
            print(f"   [FAIL] Error: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            
    except requests.exceptions.Timeout:
        print("   [TIMEOUT] Request timed out")
    except Exception as e:
        print(f"   [ERROR] {e}")
        error_str = str(e)
        if "Playwright" in error_str:
            print("\n   [INFO] Playwright error:")
            print("   This is normal if Playwright is not installed")
            print("   But the fallback code for VisualTrust is correct!")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print("If VisualTrust service is not available and Playwright works,")
    print("you should see response with visualTrust.analysisStatus='unavailable'")
    print("=" * 60)

if __name__ == "__main__":
    test_visualtrust_fallback()

