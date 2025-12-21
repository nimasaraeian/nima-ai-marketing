"""
تست ساده برای endpoint /analyze-url
"""
import requests
import json
import sys

BACKEND_URL = "http://127.0.0.1:8000"

def test_health():
    """بررسی سلامت سرور"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ سرور در حال اجرا است")
            return True
        else:
            print(f"❌ سرور پاسخ نمی‌دهد (Status: {response.status_code})")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ سرور در حال اجرا نیست. لطفا ابتدا سرور را راه‌اندازی کنید:")
        print("   python run_api.py")
        return False
    except Exception as e:
        print(f"❌ خطا در اتصال: {e}")
        return False

def test_analyze_url(url="https://example.com"):
    """تست endpoint /analyze-url"""
    print(f"\n{'='*60}")
    print(f"تست تحلیل URL: {url}")
    print(f"{'='*60}\n")
    
    try:
        payload = {
            "url": url,
            "refresh": False
        }
        
        print("📤 ارسال درخواست...")
        response = requests.post(
            f"{BACKEND_URL}/analyze-url",
            json=payload,
            timeout=60
        )
        
        print(f"📥 وضعیت پاسخ: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✅ تست موفق بود!")
            print(f"\n📊 خلاصه نتایج:")
            print(f"   - وضعیت تحلیل: {result.get('analysisStatus', 'N/A')}")
            print(f"   - URL: {result.get('url', 'N/A')}")
            
            # Visual Trust
            visual = result.get('visualTrust', {})
            print(f"\n   🎨 Visual Trust:")
            print(f"      - وضعیت: {visual.get('analysisStatus', 'N/A')}")
            print(f"      - برچسب: {visual.get('label', 'N/A')}")
            print(f"      - اطمینان: {visual.get('confidence', 'N/A')}")
            
            # Brain Analysis
            brain = result.get('brain', {})
            if brain:
                print(f"\n   🧠 Brain Analysis:")
                print(f"      - Friction Score: {brain.get('frictionScore', 'N/A')}")
                print(f"      - Trust Score: {brain.get('trustScore', 'N/A')}")
                print(f"      - Clarity Score: {brain.get('clarityScore', 'N/A')}")
                print(f"      - Decision Probability: {brain.get('decisionProbability', 'N/A')}")
            
            # Features
            features = result.get('features', {})
            if features:
                print(f"\n   📋 Features:")
                print(f"      - Schema Version: {result.get('featuresSchemaVersion', 'N/A')}")
                visual_features = features.get('visual', {})
                text_features = features.get('text', {})
                print(f"      - Visual Features: {len(visual_features)} فیلد")
                print(f"      - Text Features: {len(text_features)} فیلد")
            
            # Debug Info
            debug_path = result.get('debugScreenshotPath')
            if debug_path:
                print(f"\n   📸 Screenshot: {debug_path}")
            
            # Cache Info
            cache_info = result.get('_cache', {})
            if cache_info:
                print(f"\n   💾 Cache: {'Hit' if cache_info.get('hit') else 'Miss'}")
            
            # Errors
            error = result.get('error')
            if error:
                print(f"\n   ⚠️  خطا: {error}")
            
            print(f"\n{'='*60}")
            return True
        else:
            print(f"\n❌ خطا در پاسخ سرور:")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ درخواست timeout شد (بیش از 60 ثانیه)")
        return False
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*60)
    print("🧪 تست سیستم تحلیل URL")
    print("="*60)
    
    # Test 1: Health Check
    if not test_health():
        sys.exit(1)
    
    # Test 2: Analyze URL
    test_url = "https://example.com"
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    
    success = test_analyze_url(test_url)
    
    if success:
        print("\n✅ همه تست‌ها موفق بودند!")
    else:
        print("\n❌ برخی تست‌ها ناموفق بودند")
        sys.exit(1)

if __name__ == "__main__":
    main()

