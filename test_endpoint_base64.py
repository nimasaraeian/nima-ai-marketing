"""Test the actual API endpoint to verify Base64 data URLs in response."""
import requests
import json
import sys

def test_endpoint():
    """Test the test-capture endpoint returns Base64 data URLs."""
    print("🧪 Testing /api/analyze/url-human/test-capture endpoint...")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:8000"
    endpoint = f"{base_url}/api/analyze/url-human/test-capture"
    
    payload = {
        "url": "https://example.com",
        "goal": "leads",
        "locale": "en"
    }
    
    try:
        print(f"📡 Sending request to: {endpoint}")
        print(f"📋 Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        
        print(f"\n📥 Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Request failed: {response.text}")
            return False
        
        data = response.json()
        
        # Check response structure
        if data.get("analysisStatus") != "ok":
            print(f"❌ Analysis status is not 'ok': {data.get('analysisStatus')}")
            return False
        
        # Check screenshots
        capture = data.get("capture", {})
        screenshots = capture.get("screenshots", {})
        
        desktop = screenshots.get("desktop", {})
        mobile = screenshots.get("mobile", {})
        
        print("\n📊 Screenshot Data URLs:")
        
        # Check desktop
        desktop_atf = desktop.get("above_the_fold_data_url")
        desktop_full = desktop.get("full_page_data_url")
        
        if desktop_atf and desktop_atf.startswith("data:image/png;base64,"):
            print(f"  ✅ Desktop ATF: {len(desktop_atf)} chars (valid)")
        else:
            print(f"  ❌ Desktop ATF: Missing or invalid")
            return False
            
        if desktop_full and desktop_full.startswith("data:image/png;base64,"):
            print(f"  ✅ Desktop Full: {len(desktop_full)} chars (valid)")
        else:
            print(f"  ❌ Desktop Full: Missing or invalid")
            return False
        
        # Check mobile
        mobile_atf = mobile.get("above_the_fold_data_url")
        mobile_full = mobile.get("full_page_data_url")
        
        if mobile_atf and mobile_atf.startswith("data:image/png;base64,"):
            print(f"  ✅ Mobile ATF: {len(mobile_atf)} chars (valid)")
        else:
            print(f"  ❌ Mobile ATF: Missing or invalid")
            return False
            
        if mobile_full and mobile_full.startswith("data:image/png;base64,"):
            print(f"  ✅ Mobile Full: {len(mobile_full)} chars (valid)")
        else:
            print(f"  ❌ Mobile Full: Missing or invalid")
            return False
        
        # Verify legacy fields are None
        if desktop.get("above_the_fold") is not None:
            print(f"  ⚠️  Legacy desktop.above_the_fold should be None but is: {desktop.get('above_the_fold')}")
        if mobile.get("above_the_fold") is not None:
            print(f"  ⚠️  Legacy mobile.above_the_fold should be None but is: {mobile.get('above_the_fold')}")
        
        print("\n🎉 All endpoint tests passed! Base64 data URLs are working correctly.")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is the backend running on http://127.0.0.1:8000?")
        print("   Start it with: uvicorn api.app:app --reload")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_endpoint()
    sys.exit(0 if success else 1)




