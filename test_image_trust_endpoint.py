"""
Test script for the visual trust analysis endpoint
"""
import requests
import sys
from pathlib import Path

# Test the endpoint
API_URL = "http://127.0.0.1:8000/api/analyze/image-trust"
TEST_IMAGE = "test_image.jpg"

def test_endpoint():
    """Test the image trust endpoint"""
    if not Path(TEST_IMAGE).exists():
        print(f"❌ Test image not found: {TEST_IMAGE}")
        print("   Please ensure test_image.jpg exists in the project root")
        return False
    
    try:
        print(f"📤 Sending request to {API_URL}...")
        with open(TEST_IMAGE, 'rb') as f:
            files = {'file': (TEST_IMAGE, f, 'image/jpeg')}
            response = requests.post(API_URL, files=files)
        
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response headers: {dict(response.headers)}")
        
        if response.ok:
            data = response.json()
            print(f"✅ Success! Response: {data}")
            if data.get('success') and data.get('analysis'):
                print(f"   Trust label: {data['analysis'].get('trust_label')}")
                print(f"   Trust scores: {data['analysis'].get('trust_scores')}")
                return True
            else:
                print("❌ Response format incorrect")
                return False
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Is the API server running?")
        print("   Start it with: python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000")
        return False
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_endpoint()
    sys.exit(0 if success else 1)

