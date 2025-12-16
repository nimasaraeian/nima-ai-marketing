#!/usr/bin/env python3
"""
Demo stability check for analyze-url endpoint.
Tests encoding, VisualTrust, and response structure.
"""
import sys
import requests
import json
import re
from typing import Dict, Any, List

URL = "https://nimasaraeian.com/"
ENDPOINT = "http://127.0.0.1:8000/analyze-url?refresh=1"
NUM_TESTS = 10


def check_encoding(text: str) -> bool:
    """Check if text contains mojibake markers."""
    if not text:
        return True
    return not bool(re.search(r'[Ââ]|Letâs|Â·', text))


def run_test(test_num: int) -> tuple:
    """Run a single test and return (success, errors)."""
    errors = []
    
    try:
        response = requests.post(
            ENDPOINT,
            json={"url": URL},
            timeout=60,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        data = response.json()
        
        # Check encoding gate
        extracted_text = data.get("extractedText", "")
        if not check_encoding(extracted_text):
            errors.append(f"Encoding issue found in extractedText")
            return False, errors
        
        # Check analysisStatus
        if data.get("analysisStatus") != "ok":
            errors.append(f"analysisStatus={data.get('analysisStatus')}")
            return False, errors
        
        # Check visualTrust structure
        vt = data.get("visualTrust")
        if not vt:
            errors.append("visualTrust missing")
            return False, errors
        
        if not isinstance(vt, dict):
            errors.append("visualTrust is not a dict")
            return False, errors
        
        # Check required keys
        required_keys = ["analysisStatus", "label", "confidence", "warnings", "elements", "narrative"]
        missing_keys = [k for k in required_keys if k not in vt]
        if missing_keys:
            errors.append(f"visualTrust missing keys: {', '.join(missing_keys)}")
            return False, errors
        
        # Check label is not null
        if vt.get("label") is None or vt.get("label") == "":
            errors.append("visualTrust.label is null or empty")
            return False, errors
        
        # Check narrative is non-empty
        narrative = vt.get("narrative", [])
        if not narrative or len(narrative) == 0:
            errors.append("visualTrust.narrative is empty")
            return False, errors
        
        # Check debugBuild
        debug_build = data.get("debugBuild")
        if debug_build != "DEMO_READY_V1":
            errors.append(f"debugBuild={debug_build} (expected DEMO_READY_V1)")
        
        # Check screenshot bytes
        screenshot_bytes = data.get("debugScreenshotBytes", 0)
        if screenshot_bytes < 50000:
            errors.append(f"screenshot bytes={screenshot_bytes} (< 50000)")
        
        # Success
        print(f"Test {test_num}/10: OK (status={data.get('analysisStatus')}, "
              f"vt_label={vt.get('label')}, vt_conf={vt.get('confidence')}, "
              f"screenshot={screenshot_bytes} bytes)")
        return True, errors
        
    except requests.exceptions.RequestException as e:
        errors.append(f"Request exception: {e}")
        return False, errors
    except json.JSONDecodeError as e:
        errors.append(f"JSON decode error: {e}")
        return False, errors
    except Exception as e:
        errors.append(f"Unexpected error: {e}")
        return False, errors


def main():
    """Run all tests."""
    print("=" * 50)
    print("Demo Check - Running 10 tests")
    print("=" * 50)
    print()
    
    success_count = 0
    fail_count = 0
    all_errors = []
    
    for i in range(1, NUM_TESTS + 1):
        print(f"Test {i}/10...", end="", flush=True)
        success, errors = run_test(i)
        
        if success:
            success_count += 1
        else:
            fail_count += 1
            print(f" FAILED ({'; '.join(errors)})")
            all_errors.extend([f"Test {i}: {e}" for e in errors])
    
    print()
    print("=" * 50)
    print(f"Results: {success_count} passed, {fail_count} failed")
    print("=" * 50)
    
    if all_errors:
        print()
        print("Errors:")
        for error in all_errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print()
        print("All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()

