"""
بررسی و رفع خطای "Method Not Allowed"
"""
import requests
import json
import sys

BACKEND_URL = "http://127.0.0.1:8000"

def check_server():
    """بررسی سلامت سرور"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def test_correct_usage():
    """تست استفاده صحیح"""
    print("="*60)
    print("✅ تست استفاده صحیح از /analyze-url")
    print("="*60)
    
    if not check_server():
        print("\n❌ سرور در حال اجرا نیست!")
        print("   لطفا ابتدا سرور را راه‌اندازی کنید:")
        print("   python run_api.py")
        return
    
    try:
        payload = {
            "url": "https://example.com"
        }
        
        print(f"\n📤 ارسال درخواست POST به /analyze-url...")
        print(f"   Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{BACKEND_URL}/analyze-url",
            json=payload,
            timeout=60
        )
        
        print(f"\n📥 پاسخ:")
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ موفق! درخواست صحیح است.")
            result = response.json()
            print(f"\n   📊 خلاصه:")
            print(f"      - وضعیت: {result.get('analysisStatus', 'N/A')}")
            print(f"      - URL: {result.get('url', 'N/A')}")
        elif response.status_code == 405:
            print("   ❌ Method Not Allowed!")
            print(f"   ⚠️  این خطا یعنی از روش HTTP اشتباه استفاده شده")
            print(f"   ✅ باید از POST استفاده کنید، نه GET")
            allowed = response.headers.get("Allow", "N/A")
            print(f"   📋 Allowed methods: {allowed}")
        elif response.status_code == 404:
            print("   ❌ Not Found!")
            print(f"   ⚠️  این خطا یعنی path اشتباه است")
            print(f"   ✅ path صحیح: /analyze-url (بدون /api/)")
        elif response.status_code == 422:
            print("   ❌ Validation Error!")
            try:
                error = response.json()
                print(f"   📋 جزئیات: {error.get('detail', error)}")
            except:
                print(f"   📋 Response: {response.text[:200]}")
        else:
            print(f"   ⚠️  خطای دیگر: {response.status_code}")
            print(f"   📋 Response: {response.text[:200]}")
            
    except requests.exceptions.Timeout:
        print("\n⏱️  درخواست timeout شد (بیش از 60 ثانیه)")
        print("   این طبیعی است - تحلیل ممکن است طول بکشد")
    except Exception as e:
        print(f"\n❌ خطا: {e}")
        import traceback
        traceback.print_exc()

def show_common_errors():
    """نمایش خطاهای رایج و راه حل‌ها"""
    print("\n" + "="*60)
    print("🔍 خطاهای رایج و راه حل‌ها")
    print("="*60)
    
    errors = [
        {
            "error": "Method Not Allowed (405)",
            "علت": "استفاده از GET به جای POST",
            "راه حل": "از POST استفاده کنید: requests.post(...)"
        },
        {
            "error": "Not Found (404)",
            "علت": "path اشتباه (مثلاً /api/analyze-url)",
            "راه حل": "از /analyze-url استفاده کنید (بدون /api/)"
        },
        {
            "error": "Validation Error (422)",
            "علت": "فیلد url در body موجود نیست",
            "راه حل": "مطمئن شوید body شامل {'url': '...'} است"
        },
        {
            "error": "Connection Error",
            "علت": "سرور در حال اجرا نیست",
            "راه حل": "ابتدا سرور را راه‌اندازی کنید: python run_api.py"
        }
    ]
    
    for i, err in enumerate(errors, 1):
        print(f"\n{i}. {err['error']}")
        print(f"   علت: {err['علت']}")
        print(f"   راه حل: {err['راه حل']}")

def show_examples():
    """نمایش مثال‌های استفاده صحیح"""
    print("\n" + "="*60)
    print("📝 مثال‌های استفاده صحیح")
    print("="*60)
    
    examples = [
        {
            "title": "Python (requests)",
            "code": """
import requests

response = requests.post(
    "http://127.0.0.1:8000/analyze-url",
    json={"url": "https://example.com"}
)
print(response.json())
"""
        },
        {
            "title": "cURL",
            "code": """
curl -X POST http://127.0.0.1:8000/analyze-url \\
  -H "Content-Type: application/json" \\
  -d '{"url": "https://example.com"}'
"""
        },
        {
            "title": "JavaScript (fetch)",
            "code": """
fetch('http://127.0.0.1:8000/analyze-url', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({url: 'https://example.com'})
})
.then(r => r.json())
.then(console.log);
"""
        }
    ]
    
    for ex in examples:
        print(f"\n{ex['title']}:")
        print(ex['code'])

def main():
    print("="*60)
    print("🔧 بررسی خطای 'Method Not Allowed'")
    print("="*60)
    
    # تست استفاده صحیح
    test_correct_usage()
    
    # نمایش خطاهای رایج
    show_common_errors()
    
    # نمایش مثال‌ها
    show_examples()
    
    print("\n" + "="*60)
    print("💡 نکته: همیشه از POST و path /analyze-url استفاده کنید")
    print("="*60)

if __name__ == "__main__":
    main()










