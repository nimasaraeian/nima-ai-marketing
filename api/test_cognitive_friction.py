"""Test script for cognitive friction endpoint"""
import requests

url = "http://localhost:8000/api/brain/cognitive-friction"

payload = {
    "raw_text": "Our new AI marketing platform helps you grow your business. Sign up today and discover the power of AI-driven optimization.",
    "platform": "landing_page",
    "goal": ["leads"],
    "audience": "cold",
    "language": "en",
    "meta": None
}

print("Testing cognitive friction endpoint...")
print(f"URL: {url}")
print(f"Payload: {payload}")
print("\n" + "="*60)

try:
    res = requests.post(url, json=payload)
    print(f"Status Code: {res.status_code}")
    print("\nResponse:")
    print(res.json())
except requests.exceptions.ConnectionError:
    print("ERROR: Could not connect to server.")
    print("Make sure the FastAPI server is running on http://localhost:8000")
    print("\nStart the server with:")
    print("  python -m uvicorn api.main:app --host localhost --port 8000 --reload")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

