"""Test script for rewrite endpoint"""
import requests
import json

payload = {
    "text": "Limited time offer!",
    "platform": "ad",
    "goal": ["sales"],
    "audience": "cold",
    "language": "en"
}

res = requests.post("http://localhost:8000/api/brain/rewrite", json=payload)
print(res.status_code)
print(res.text)
