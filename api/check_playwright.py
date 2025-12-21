"""
Check if Playwright and Chromium are properly installed.

Usage:
    python api/check_playwright.py
"""
import sys
from pathlib import Path

def check_playwright():
    """Check if Playwright is installed and browsers are available."""
    print("=" * 60)
    print("Playwright Installation Check")
    print("=" * 60)
    
    # Check if playwright package is installed
    try:
        import playwright
        print("[OK] Playwright package installed")
    except ImportError:
        print("[ERROR] Playwright package not installed")
        print("   Install with: pip install playwright")
        return False
    
    # Check if browsers are installed
    try:
        from playwright.sync_api import sync_playwright
        
        print("\nChecking browser installation...")
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                print("[OK] Chromium browser is installed and working")
                browser.close()
                return True
            except Exception as e:
                print(f"[ERROR] Chromium browser not available: {type(e).__name__}: {str(e)}")
                print("\nTo install Chromium, run:")
                print("   python -m playwright install chromium")
                return False
    except Exception as e:
        print(f"[ERROR] Error checking browsers: {type(e).__name__}: {str(e)}")
        return False

if __name__ == "__main__":
    success = check_playwright()
    sys.exit(0 if success else 1)

