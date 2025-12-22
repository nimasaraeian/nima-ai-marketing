#!/usr/bin/env python3
"""
Test script to verify all imports work correctly
Run this to check if there are any import issues before deployment
"""
import sys
import traceback

def test_imports():
    """Test all critical imports"""
    errors = []
    
    # Test main app import
    try:
        from api.main import app
        print("✅ api.main import: SUCCESS")
    except Exception as e:
        errors.append(f"❌ api.main import FAILED: {e}")
        traceback.print_exc()
    
    # Test critical modules
    modules_to_test = [
        "api.visual_trust_engine",
        "api.services.image_trust_service",
        "api.cognitive_friction_engine",
        "api.decision_engine",
        "api.psychology_engine",
        "api.chat",
        "api.brain_loader",
    ]
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module}: SUCCESS")
        except Exception as e:
            errors.append(f"❌ {module}: FAILED - {e}")
    
    if errors:
        print("\n" + "="*60)
        print("IMPORT ERRORS FOUND:")
        print("="*60)
        for error in errors:
            print(error)
        return False
    else:
        print("\n" + "="*60)
        print("✅ ALL IMPORTS SUCCESSFUL - Ready for deployment!")
        print("="*60)
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)








