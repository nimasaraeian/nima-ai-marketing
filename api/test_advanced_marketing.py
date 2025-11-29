"""
تست پیشرفته Marketing - بررسی کیفیت پاسخ AI
"""
import sys
import io
import requests
import json
import time

# Fix encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

API_URL = "http://localhost:8000/chat"

# سوال پیچیده و واقعی
TEST_QUESTION = """یک کلینیک زیبایی در استانبول دارم که خدمات زیر را ارائه می‌دهد:
- بوتاکس
- فیلر
- لیزر موهای زائد
- میکرونیدلینگ

بودجه ماهانه: 5000 دلار
مشکل: CTR پایین (0.3%)، CPC بالا (8 دلار)، تبدیل پایین (1.2%)

لطفاً یک تحلیل کامل و استراتژی عملی بده که شامل:
1. تشخیص علت مشکلات
2. مثال‌های عینی از ad headlines و hooks
3. پیشنهادات محلی برای استانبول (tourists vs locals)
4. برنامه عملی 0-7 روز و 7-30 روز
5. اهداف عددی واقع‌بینانه"""

def check_server():
    """بررسی وضعیت سرور"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def test_marketing_question():
    """تست سوال مارکتینگ"""
    print("=" * 80)
    print("🧪 تست پیشرفته Marketing AI")
    print("=" * 80)
    print()
    
    # بررسی سرور
    print("📡 بررسی اتصال به سرور...")
    if not check_server():
        print("❌ سرور در حال اجرا نیست!")
        print("   لطفاً ابتدا سرور را راه‌اندازی کنید:")
        print("   python -m uvicorn api.app:app --host localhost --port 8000")
        return
    print("✅ سرور آماده است")
    print()
    
    # ارسال درخواست
    print("📤 ارسال سوال به AI...")
    print("-" * 80)
    print(f"سوال: {TEST_QUESTION[:100]}...")
    print("-" * 80)
    print()
    
    try:
        start_time = time.time()
        
        response = requests.post(
            API_URL,
            json={
                "message": TEST_QUESTION,
                "model": "gpt-4o-mini",
                "temperature": 0.7
            },
            timeout=120
        )
        
        elapsed_time = time.time() - start_time
        
        if response.status_code != 200:
            print(f"❌ خطا: {response.status_code}")
            print(response.text)
            return
        
        result = response.json()
        ai_response = result.get("response", "")
        
        print("=" * 80)
        print("✅ پاسخ دریافت شد!")
        print("=" * 80)
        print(f"⏱️  زمان پاسخ: {elapsed_time:.2f} ثانیه")
        print(f"📏 طول پاسخ: {len(ai_response)} کاراکتر")
        print()
        
        # تحلیل کیفیت پاسخ
        print("=" * 80)
        print("📊 تحلیل کیفیت پاسخ")
        print("=" * 80)
        print()
        
        checks = {
            "مثال‌های عینی (Headlines/Hooks)": [
                "headline" in ai_response.lower(),
                "hook" in ai_response.lower(),
                '"' in ai_response or '«' in ai_response or "'" in ai_response
            ],
            "محلی‌سازی Istanbul": [
                "istanbul" in ai_response.lower() or "استانبول" in ai_response,
                "tourist" in ai_response.lower() or "گردشگر" in ai_response,
                "local" in ai_response.lower() or "محلی" in ai_response
            ],
            "برنامه عملی (0-7 روز)": [
                "0-7" in ai_response or "0 تا 7" in ai_response or "هفته اول" in ai_response,
                "action" in ai_response.lower() or "اقدام" in ai_response
            ],
            "برنامه عملی (7-30 روز)": [
                "7-30" in ai_response or "7 تا 30" in ai_response or "ماه اول" in ai_response
            ],
            "اهداف عددی": [
                any(char.isdigit() for char in ai_response[:500]),
                "%" in ai_response or "درصد" in ai_response
            ],
            "تحلیل علت (Root Cause)": [
                "علت" in ai_response or "cause" in ai_response.lower(),
                "مشکل" in ai_response or "problem" in ai_response.lower()
            ],
            "4P Scan": [
                "product" in ai_response.lower() or "محصول" in ai_response,
                "price" in ai_response.lower() or "قیمت" in ai_response,
                "promotion" in ai_response.lower() or "تبلیغ" in ai_response
            ]
        }
        
        score = 0
        total = len(checks)
        
        for check_name, conditions in checks.items():
            passed = any(conditions)
            status = "✅" if passed else "❌"
            print(f"{status} {check_name}: {'گذراند' if passed else 'نیافت'}")
            if passed:
                score += 1
        
        print()
        print("-" * 80)
        print(f"📈 امتیاز کیفیت: {score}/{total} ({score*100//total}%)")
        print("-" * 80)
        print()
        
        # نمایش پاسخ کامل
        print("=" * 80)
        print("💬 پاسخ کامل AI")
        print("=" * 80)
        print()
        print(ai_response)
        print()
        print("=" * 80)
        
        # ذخیره پاسخ
        with open("api/test_advanced_response.md", "w", encoding="utf-8") as f:
            f.write("# تست پیشرفته Marketing AI\n\n")
            f.write(f"**تاریخ:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**زمان پاسخ:** {elapsed_time:.2f} ثانیه\n\n")
            f.write(f"**طول پاسخ:** {len(ai_response)} کاراکتر\n\n")
            f.write(f"**امتیاز کیفیت:** {score}/{total}\n\n")
            f.write("## سوال\n\n")
            f.write(f"{TEST_QUESTION}\n\n")
            f.write("## پاسخ AI\n\n")
            f.write(f"{ai_response}\n")
        
        print("💾 پاسخ در فایل 'api/test_advanced_response.md' ذخیره شد")
        print()
        
    except requests.exceptions.Timeout:
        print("❌ خطا: Timeout - سرور پاسخ نداد")
    except requests.exceptions.ConnectionError:
        print("❌ خطا: نمی‌توان به سرور متصل شد")
    except Exception as e:
        print(f"❌ خطای غیرمنتظره: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_marketing_question()



