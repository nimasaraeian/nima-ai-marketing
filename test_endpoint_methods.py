"""
بررسی روش‌های HTTP برای endpoint ها
"""
import requests
import json

BACKEND_URL = "http://127.0.0.1:8000"

def test_endpoint_methods():
    """بررسی روش‌های مختلف HTTP برای endpoint ها"""
    
    endpoints = [
        ("/analyze-url", "POST"),
        ("/api/analyze-url", "POST"),
        ("/health", "GET"),
        ("/", "GET"),
    ]
    
    print("="*60)
    print("🔍 بررسی روش‌های HTTP برای endpoint ها")
    print("="*60)
    
    for endpoint, method in endpoints:
        try:
            url = f"{BACKEND_URL}{endpoint}"
            print(f"\n📡 تست: {method} {endpoint}")
            
            if method == "GET":
                response = requests.get(url, timeout=5)
            elif method == "POST":
                # تست با payload ساده
                payload = {"url": "https://example.com"}
                response = requests.post(url, json=payload, timeout=5)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ موفق")
            elif response.status_code == 405:
                print(f"   ❌ Method Not Allowed - از {method} استفاده شده")
                # بررسی allowed methods
                allowed = response.headers.get("Allow", "N/A")
                print(f"   Allowed methods: {allowed}")
            elif response.status_code == 404:
                print(f"   ❌ Not Found - endpoint یافت نشد")
            else:
                try:
                    error = response.json()
                    print(f"   ⚠️  خطا: {error.get('detail', response.text[:100])}")
                except:
                    print(f"   ⚠️  خطا: {response.text[:100]}")
                    
        except requests.exceptions.ConnectionError:
            print(f"   ❌ سرور در حال اجرا نیست")
            break
        except Exception as e:
            print(f"   ❌ خطا: {e}")
    
    print("\n" + "="*60)
    print("💡 راهنمایی:")
    print("   - endpoint /analyze-url باید با POST استفاده شود")
    print("   - payload باید شامل {'url': '...'} باشد")
    print("="*60)

if __name__ == "__main__":
    test_endpoint_methods()













