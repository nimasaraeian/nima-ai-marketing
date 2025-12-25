"""Test script to verify Base64 screenshot data URLs work correctly."""
import asyncio
import sys
from api.services.page_capture import capture_page_artifacts

async def test_capture():
    """Test that capture_page_artifacts returns Base64 data URLs."""
    print("🧪 Testing screenshot capture with Base64 data URLs...")
    print("=" * 60)
    
    try:
        # Test with a simple URL
        url = "https://example.com"
        print(f"📸 Capturing: {url}")
        
        result = await capture_page_artifacts(url)
        
        # Check structure
        screenshots = result.get("screenshots", {})
        desktop = screenshots.get("desktop", {})
        mobile = screenshots.get("mobile", {})
        
        # Verify desktop data URLs
        desktop_atf = desktop.get("above_the_fold_data_url")
        desktop_full = desktop.get("full_page_data_url")
        
        # Verify mobile data URLs
        mobile_atf = mobile.get("above_the_fold_data_url")
        mobile_full = mobile.get("full_page_data_url")
        
        print("\n✅ Capture completed successfully!")
        print("\n📊 Results:")
        print(f"  Desktop ATF data URL: {desktop_atf[:50] if desktop_atf else 'MISSING'}...")
        print(f"  Desktop Full data URL: {desktop_full[:50] if desktop_full else 'MISSING'}...")
        print(f"  Mobile ATF data URL: {mobile_atf[:50] if mobile_atf else 'MISSING'}...")
        print(f"  Mobile Full data URL: {mobile_full[:50] if mobile_full else 'MISSING'}...")
        
        # Validate data URLs
        errors = []
        if not desktop_atf or not desktop_atf.startswith("data:image/png;base64,"):
            errors.append("❌ Desktop ATF data URL is invalid")
        else:
            print("  ✅ Desktop ATF data URL is valid")
            
        if not desktop_full or not desktop_full.startswith("data:image/png;base64,"):
            errors.append("❌ Desktop Full data URL is invalid")
        else:
            print("  ✅ Desktop Full data URL is valid")
            
        if not mobile_atf or not mobile_atf.startswith("data:image/png;base64,"):
            errors.append("❌ Mobile ATF data URL is invalid")
        else:
            print("  ✅ Mobile ATF data URL is valid")
            
        if not mobile_full or not mobile_full.startswith("data:image/png;base64,"):
            errors.append("❌ Mobile Full data URL is invalid")
        else:
            print("  ✅ Mobile Full data URL is valid")
        
        # Check data URL lengths (should be substantial)
        if desktop_atf and len(desktop_atf) < 1000:
            errors.append(f"⚠️  Desktop ATF data URL seems too short: {len(desktop_atf)} chars")
        if mobile_atf and len(mobile_atf) < 1000:
            errors.append(f"⚠️  Mobile ATF data URL seems too short: {len(mobile_atf)} chars")
        
        if errors:
            print("\n❌ Errors found:")
            for error in errors:
                print(f"  {error}")
            return False
        else:
            print("\n🎉 All tests passed! Base64 data URLs are working correctly.")
            return True
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_capture())
    sys.exit(0 if success else 1)




