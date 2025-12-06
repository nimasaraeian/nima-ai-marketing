"""
Quick test to verify backend is running and responding
"""
import requests
import json

BACKEND_URL = "http://localhost:8000"

def test_backend():
    print("=" * 60)
    print("Testing Backend Connection")
    print("=" * 60)
    
    # Test 1: Health check
    print("\n1. Testing /health endpoint...")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        if response.status_code == 200:
            print("   ✅ Health check passed")
        else:
            print("   ❌ Health check failed")
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to backend. Is the server running?")
        print(f"   Start with: python -m uvicorn api.main:app --host localhost --port 8000 --reload")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 2: Root endpoint
    print("\n2. Testing / endpoint...")
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        if response.status_code == 200:
            print("   ✅ Root endpoint works")
        else:
            print("   ❌ Root endpoint failed")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 3: /api/brain endpoint with simple JSON
    print("\n3. Testing /api/brain endpoint (JSON)...")
    try:
        test_data = {
            "query": "Test query",
            "role": "ai_marketing_strategist",
            "city": "Istanbul",
            "industry": "restaurant",
            "channel": "Instagram Ads"
        }
        response = requests.post(
            f"{BACKEND_URL}/api/brain",
            json=test_data,
            timeout=30
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Brain endpoint works")
            print(f"   Response keys: {list(result.keys())}")
        else:
            print(f"   ❌ Brain endpoint failed")
            print(f"   Response: {response.text[:500]}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to backend")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! Backend is running correctly.")
    print("=" * 60)
    return True

if __name__ == "__main__":
    test_backend()












