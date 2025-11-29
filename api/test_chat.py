"""
Test script to send a request to the AI Brain API
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

url = "http://localhost:8000/chat"
payload = {
    "message": "یک مقاله ۷ بخشی برای AI Marketing 2026 بنویس. فقط مراحل کار را بده، نه متن مقاله را."
}

# Try multiple times in case server is starting
max_retries = 3
for attempt in range(max_retries):
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        print("=" * 60)
        print("API RESPONSE")
        print("=" * 60)
        print()
        result = response.json()
        print(result["response"])
        print()
        print("=" * 60)
        sys.exit(0)
        
    except requests.exceptions.ConnectionError:
        if attempt < max_retries - 1:
            print(f"Waiting for server to start... (attempt {attempt + 1}/{max_retries})")
            time.sleep(3)
        else:
            print("ERROR: Could not connect to API server.")
            print()
            print("To start the server, run:")
            print("  cd C:\\Users\\USER\\Desktop\\tensorflow-nima")
            print("  uvicorn api.app:app --reload")
            print()
            print("Or make sure:")
            print("  1. Server is running on http://localhost:8000")
            print("  2. OPENAI_API_KEY environment variable is set")
            sys.exit(1)
    except requests.exceptions.Timeout:
        print("ERROR: Request timed out.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

