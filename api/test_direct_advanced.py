"""
تست مستقیم پیشرفته - بدون API
"""
import sys
import io
from pathlib import Path

# Fix encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add api to path
api_dir = Path(__file__).parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from chat import chat_completion

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

def test_advanced():
    """تست پیشرفته"""
    print("=" * 80)
    print("🧪 تست پیشرفته Marketing AI (مستقیم)")
    print("=" * 80)
    print()
    
    print("📤 ارسال سوال به AI...")
    print("-" * 80)
    print(f"سوال: {TEST_QUESTION[:100]}...")
    print("-" * 80)
    print()
    print("⏳ در حال پردازش (این ممکن است چند ثانیه طول بکشد)...")
    print()
    
    try:
        import time
        start_time = time.time()
        
        response = chat_completion(
            user_message=TEST_QUESTION,
            model="gpt-4o-mini",
            temperature=0.7
        )
        
        elapsed_time = time.time() - start_time
        
        print("=" * 80)
        print("✅ پاسخ دریافت شد!")
        print("=" * 80)
        print(f"⏱️  زمان پاسخ: {elapsed_time:.2f} ثانیه")
        print(f"📏 طول پاسخ: {len(response)} کاراکتر")
        print()
        
        # تحلیل کیفیت پاسخ
        print("=" * 80)
        print("📊 تحلیل کیفیت پاسخ")
        print("=" * 80)
        print()
        
        checks = {
            "مثال‌های عینی (Headlines/Hooks)": [
                "headline" in response.lower(),
                "hook" in response.lower(),
                '"' in response or '«' in response or "'" in response,
                "مثال" in response
            ],
            "محلی‌سازی Istanbul": [
                "istanbul" in response.lower() or "استانبول" in response,
                "tourist" in response.lower() or "گردشگر" in response or "توریست" in response,
                "local" in response.lower() or "محلی" in response
            ],
            "برنامه عملی (0-7 روز)": [
                "0-7" in response or "0 تا 7" in response or "هفته اول" in response or "روز اول" in response,
                "action" in response.lower() or "اقدام" in response or "برنامه" in response
            ],
            "برنامه عملی (7-30 روز)": [
                "7-30" in response or "7 تا 30" in response or "ماه اول" in response or "هفته دوم" in response
            ],
            "اهداف عددی": [
                any(char.isdigit() for char in response[:500]),
                "%" in response or "درصد" in response
            ],
            "تحلیل علت (Root Cause)": [
                "علت" in response or "cause" in response.lower(),
                "مشکل" in response or "problem" in response.lower(),
                "ریشه" in response
            ],
            "4P Scan": [
                "product" in response.lower() or "محصول" in response,
                "price" in response.lower() or "قیمت" in response,
                "promotion" in response.lower() or "تبلیغ" in response
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
        print(response)
        print()
        print("=" * 80)
        
        # ذخیره پاسخ
        output_file = api_dir / "test_advanced_response.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# تست پیشرفته Marketing AI\n\n")
            f.write(f"**تاریخ:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**زمان پاسخ:** {elapsed_time:.2f} ثانیه\n\n")
            f.write(f"**طول پاسخ:** {len(response)} کاراکتر\n\n")
            f.write(f"**امتیاز کیفیت:** {score}/{total}\n\n")
            f.write("## سوال\n\n")
            f.write(f"{TEST_QUESTION}\n\n")
            f.write("## پاسخ AI\n\n")
            f.write(f"{response}\n")
        
        print(f"💾 پاسخ در فایل '{output_file}' ذخیره شد")
        print()
        
    except Exception as e:
        print("=" * 80)
        print(f"❌ خطا: {type(e).__name__}")
        print("=" * 80)
        print(f"{str(e)}")
        print()
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_advanced()



