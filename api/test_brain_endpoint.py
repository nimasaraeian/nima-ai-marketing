"""
Test the /api/brain endpoint
"""
import sys
import io
import requests
import json

# Fix encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

API_URL = "http://127.0.0.1:8000/api/brain"

def test_brain_endpoint():
    """Test the brain endpoint"""
    print("=" * 80)
    print("🧪 تست Endpoint /api/brain")
    print("=" * 80)
    print()
    
    # Test data
    test_data = {
        "role": "ai_marketing_strategist",
        "locale": "tr-TR",
        "city": "Istanbul",
        "industry": "restaurant",
        "channel": "Instagram Ads",
        "query": "I own a mid-range restaurant in Kadıköy, Istanbul. Here is my current Instagram ad copy: 'Delicious food, cozy vibes. Visit us tonight!' Our CTR is low and people save the post but don't click. Analyze this ad using behavioral marketing and AI, suggest 3-5 concrete new ad variants, and propose 2 A/B test ideas with clear metrics."
    }
    
    print("📤 ارسال درخواست...")
    print(f"URL: {API_URL}")
    print(f"Data: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    print()
    print("⏳ در حال انتظار برای پاسخ (این ممکن است 30-60 ثانیه طول بکشد)...")
    print()
    
    try:
        response = requests.post(
            API_URL,
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        
        print("=" * 80)
        print(f"📊 Status Code: {response.status_code}")
        print("=" * 80)
        print()
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ پاسخ دریافت شد!")
            print()
            print("-" * 80)
            print("📊 Quality Score:", result.get("quality_score", "N/A"), "/ 5")
            print("-" * 80)
            print()
            
            if "quality_checks" in result:
                print("🔍 Quality Checks:")
                for check, passed in result["quality_checks"].items():
                    status = "✅" if passed else "❌"
                    print(f"  {status} {check}: {passed}")
                print()
            
            print("=" * 80)
            print("💬 پاسخ کامل AI:")
            print("=" * 80)
            print()
            print(result.get("response", "No response"))
            print()
            print("=" * 80)
            
            # Save to file
            with open("api/test_brain_response.md", "w", encoding="utf-8") as f:
                f.write("# تست /api/brain Endpoint\n\n")
                f.write("## Request\n\n")
                f.write(f"```json\n{json.dumps(test_data, indent=2, ensure_ascii=False)}\n```\n\n")
                f.write("## Response\n\n")
                f.write(f"**Quality Score:** {result.get('quality_score', 'N/A')}/5\n\n")
                f.write("### Quality Checks\n\n")
                if "quality_checks" in result:
                    for check, passed in result["quality_checks"].items():
                        f.write(f"- {check}: {passed}\n")
                f.write("\n### Full Response\n\n")
                f.write(result.get("response", "No response"))
            
            print("💾 پاسخ در 'api/test_brain_response.md' ذخیره شد")
            
        else:
            print(f"❌ خطا: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.Timeout:
        print("❌ خطا: Timeout - سرور پاسخ نداد")
    except requests.exceptions.ConnectionError:
        print("❌ خطا: نمی‌توان به سرور متصل شد")
        print("   مطمئن شوید سرور در حال اجرا است:")
        print("   python -m uvicorn api.main:app --reload")
    except Exception as e:
        print(f"❌ خطای غیرمنتظره: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_brain_endpoint()



