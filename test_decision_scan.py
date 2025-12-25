"""Test script for /api/decision-scan endpoint"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_text_mode():
    """Test text mode"""
    print("Testing text mode...")
    response = requests.post(
        f"{BASE_URL}/api/decision-scan",
        json={
            "mode": "text",
            "text": "Test content for analysis"
        },
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Status: {data.get('status')}")
        print(f"Decision state: {data.get('decision_state', {}).get('label')}")
    else:
        print(f"❌ Error: {response.text}")

def test_url_mode():
    """Test URL mode"""
    print("\nTesting URL mode...")
    response = requests.post(
        f"{BASE_URL}/api/decision-scan",
        json={
            "mode": "url",
            "url": "https://nimasaraeian.com",
            "goal": "leads",
            "locale": "en"
        },
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Status: {data.get('status')}")
        print(f"Decision state: {data.get('decision_state', {}).get('label')}")
    else:
        print(f"❌ Error: {response.text}")

def test_health():
    """Test health endpoint"""
    print("\nTesting health endpoint...")
    response = requests.get(f"{BASE_URL}/api/decision-scan/health")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✅ Health check passed: {response.json()}")
    else:
        print(f"❌ Health check failed: {response.text}")

if __name__ == "__main__":
    try:
        test_health()
        test_text_mode()
        # test_url_mode()  # Uncomment to test URL mode (takes longer)
    except Exception as e:
        print(f"Error: {e}")



