"""
بررسی وضعیت سیستم - تست بدون نیاز به سرور
"""
import sys
from pathlib import Path

def check_import(module_name, description):
    """بررسی import یک ماژول"""
    try:
        __import__(module_name)
        print(f"✅ {description}")
        return True
    except ImportError as e:
        print(f"❌ {description}: {e}")
        return False
    except Exception as e:
        print(f"⚠️  {description}: {e}")
        return False

def check_file_exists(file_path, description):
    """بررسی وجود فایل"""
    path = Path(file_path)
    if path.exists():
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description}: فایل یافت نشد - {path}")
        return False

def main():
    print("="*60)
    print("🔍 بررسی وضعیت سیستم")
    print("="*60)
    
    results = []
    
    # بررسی فایل‌های اصلی
    print("\n📁 بررسی فایل‌های اصلی:")
    results.append(check_file_exists("api/main.py", "Main API"))
    results.append(check_file_exists("api/routes/analyze_url.py", "Analyze URL Route"))
    results.append(check_file_exists("requirements.txt", "Requirements"))
    results.append(check_file_exists("run_api.py", "Run API Script"))
    
    # بررسی ماژول‌های Python
    print("\n📦 بررسی ماژول‌های Python:")
    results.append(check_import("fastapi", "FastAPI"))
    results.append(check_import("uvicorn", "Uvicorn"))
    results.append(check_import("httpx", "HTTPX"))
    results.append(check_import("bs4", "BeautifulSoup"))
    results.append(check_import("pydantic", "Pydantic"))
    
    # بررسی ماژول‌های پروژه
    print("\n🔧 بررسی ماژول‌های پروژه:")
    sys.path.insert(0, str(Path(__file__).parent))
    sys.path.insert(0, str(Path(__file__).parent / "api"))
    
    try:
        from api.routes.analyze_url import router
        print("✅ Analyze URL Router")
        results.append(True)
    except Exception as e:
        print(f"❌ Analyze URL Router: {e}")
        results.append(False)
    
    try:
        from api.brain.decision_brain import analyze_decision
        print("✅ Decision Brain")
        results.append(True)
    except Exception as e:
        print(f"❌ Decision Brain: {e}")
        results.append(False)
    
    try:
        from api.visual_trust_engine import run_visual_trust_from_bytes
        print("✅ Visual Trust Engine")
        results.append(True)
    except Exception as e:
        print(f"⚠️  Visual Trust Engine: {e}")
        results.append(False)
    
    try:
        from api.services.screenshot import capture_url_png_bytes
        print("✅ Screenshot Service")
        results.append(True)
    except Exception as e:
        print(f"⚠️  Screenshot Service: {e}")
        results.append(False)
    
    # بررسی ساختار دایرکتوری
    print("\n📂 بررسی ساختار دایرکتوری:")
    results.append(check_file_exists("api/cache", "Cache Directory"))
    results.append(check_file_exists("debug_shots", "Debug Shots Directory"))
    results.append(check_file_exists("models/visual_trust_model.keras", "Visual Trust Model"))
    
    # خلاصه
    print("\n" + "="*60)
    print("📊 خلاصه نتایج:")
    print("="*60)
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"✅ موفق: {passed}/{total}")
    print(f"❌ ناموفق: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 همه چیز آماده است!")
    elif passed >= total * 0.8:
        print("\n⚠️  بیشتر موارد آماده است، اما برخی مشکلات وجود دارد")
    else:
        print("\n❌ مشکلات زیادی وجود دارد. لطفا dependencies را نصب کنید:")
        print("   pip install -r requirements.txt")
    
    print("="*60)
    
    # دستورات بعدی
    print("\n📝 مراحل بعدی:")
    print("1. راه‌اندازی سرور:")
    print("   python run_api.py")
    print("\n2. اجرای تست:")
    print("   python test_analyze_url.py")
    print("\n3. یا تست با URL خاص:")
    print("   python test_analyze_url.py https://example.com")

if __name__ == "__main__":
    main()












