"""
Test screenshot capture service.

Usage:
    python api/test_screenshot.py [url]
    
Example:
    python api/test_screenshot.py https://example.com
"""
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.page_capture import capture_page_artifacts

async def test_screenshot(url: str = "https://example.com"):
    """Test screenshot capture for a given URL."""
    print("=" * 60)
    print("Screenshot Capture Test")
    print("=" * 60)
    print(f"Testing URL: {url}\n")
    
    try:
        print("Starting capture...")
        result = await capture_page_artifacts(url)
        
        print("\n" + "=" * 60)
        print("Capture Results")
        print("=" * 60)
        
        screenshots = result.get("screenshots", {})
        
        print(f"\nDesktop Screenshots:")
        print(f"  Hero (ATF): {screenshots.get('above_the_fold', 'None')}")
        print(f"  Full Page: {screenshots.get('full_page', 'None')}")
        
        mobile = screenshots.get("mobile", {})
        if isinstance(mobile, dict):
            print(f"\nMobile Screenshot:")
            print(f"  Above Fold: {mobile.get('aboveFold', 'None')}")
        else:
            print(f"\nMobile Screenshot: {mobile}")
        
        warnings = result.get("warnings", [])
        if warnings:
            print(f"\n[WARN] Warnings ({len(warnings)}):")
            for warning in warnings:
                print(f"  - {warning}")
        else:
            print("\n[OK] No warnings")
        
        # Check if files exist
        print("\n" + "=" * 60)
        print("File Check")
        print("=" * 60)
        
        screenshot_dir = Path(__file__).parent.parent / "api" / "static" / "shots"
        
        files_to_check = {
            "Hero": screenshot_dir / "hero.png",
            "Full": screenshot_dir / "full.png",
            "Mobile": screenshot_dir / "mobile.png"
        }
        
        for name, file_path in files_to_check.items():
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"[OK] {name}: {file_path} ({size:,} bytes)")
            else:
                print(f"[ERROR] {name}: {file_path} (not found)")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Error during capture: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    
    # Set event loop policy for Windows
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    success = asyncio.run(test_screenshot(url))
    sys.exit(0 if success else 1)

