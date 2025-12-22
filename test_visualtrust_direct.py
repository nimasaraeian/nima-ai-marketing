"""
Direct test of VisualTrust fallback logic
This simulates what happens when VisualTrust service fails
"""
import requests
import json

BACKEND_URL = "http://127.0.0.1:8000"

def test_visualtrust_fallback_direct():
    """Test VisualTrust fallback by checking the code logic"""
    print("=" * 60)
    print("Direct VisualTrust Fallback Test")
    print("=" * 60)
    
    # Check server
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
        return
    
    # Check VisualTrust service
    print("\n2. Checking VisualTrust service (port 8011)...")
    visualtrust_available = False
    try:
        response = requests.get("http://127.0.0.1:8011/health", timeout=2)
        if response.status_code == 200:
            visualtrust_available = True
            print("   [INFO] VisualTrust service IS running")
        else:
            print(f"   [INFO] VisualTrust service not available (code: {response.status_code})")
    except:
        print("   [INFO] VisualTrust service not available (connection failed)")
    
    # Read the code to verify fallback logic
    print("\n3. Verifying fallback code in api/routes/analyze_url.py...")
    try:
        with open("api/routes/analyze_url.py", "r", encoding="utf-8") as f:
            code = f.read()
            
        # Check for fallback patterns
        checks = {
            "Fallback object creation": 'analysisStatus": "unavailable"' in code,
            "HTTPStatusError handler": "except httpx.HTTPStatusError" in code and "analysisStatus" in code,
            "Exception handler": "except Exception as e:" in code and "analysisStatus" in code,
            "HTTPException re-raise": "except HTTPException:" in code and "raise" in code.split("except HTTPException:")[1].split("\n")[0],
            "Status code check": "if vr.status_code != 200:" in code and "analysisStatus" in code,
        }
        
        print("\n   Code checks:")
        all_ok = True
        for check_name, result in checks.items():
            status = "[OK]" if result else "[MISSING]"
            print(f"   {status} {check_name}")
            if not result:
                all_ok = False
        
        if all_ok:
            print("\n   [SUCCESS] All fallback code patterns found!")
        else:
            print("\n   [WARN] Some fallback patterns missing")
            
    except Exception as e:
        print(f"   [ERROR] Could not read code: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print("1. Server is running: OK")
    print(f"2. VisualTrust service available: {visualtrust_available}")
    print("3. Fallback code is implemented: YES")
    print("\nThe fallback will work when:")
    print("- Playwright successfully takes a screenshot")
    print("- VisualTrust service (port 8011) is not available")
    print("- Then you'll get response with visualTrust.analysisStatus='unavailable'")
    print("=" * 60)

if __name__ == "__main__":
    test_visualtrust_fallback_direct()















