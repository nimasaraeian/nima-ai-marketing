"""
Sanity check for concrete examples and localization updates
"""
import sys
import io

# Fix encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from pathlib import Path
import re

print("=" * 60)
print("SANITY CHECK - Concrete Examples & Localization")
print("=" * 60)
print()

# Check NIMA_MARKETING_BRAIN.md
marketing_file = Path("ai_brain/NIMA_MARKETING_BRAIN.md")
if marketing_file.exists():
    content = marketing_file.read_text(encoding='utf-8')
    print("[OK] NIMA_MARKETING_BRAIN.md")
    print(f"   Size: {len(content):,} bytes")
    
    checks = []
    if "Concrete Examples Requirement" in content:
        checks.append(("Concrete Examples Requirement", True))
    else:
        checks.append(("Concrete Examples Requirement", False))
    
    if "Headline example:" in content or "Ad copy idea:" in content:
        checks.append(("Example formats", True))
    else:
        checks.append(("Example formats", False))
    
    if "Create 3 new ad creatives highlighting" in content:
        checks.append(("Action Plan concrete examples", True))
    else:
        checks.append(("Action Plan concrete examples", False))
    
    if "restaurant, clinic, aesthetic center" in content:
        checks.append(("Local service context", True))
    else:
        checks.append(("Local service context", False))
    
    for check_name, passed in checks:
        status = "[OK]" if passed else "[ERROR]"
        print(f"   {status} {check_name}")
    
    print()
else:
    print("[ERROR] NIMA_MARKETING_BRAIN.md not found")
    print()

# Check quality_engine.md
quality_file = Path("ai_brain/quality_engine.md")
if quality_file.exists():
    content = quality_file.read_text(encoding='utf-8')
    print("[OK] quality_engine.md")
    print(f"   Size: {len(content):,} bytes")
    
    checks = []
    if "EXAMPLE & LOCALIZATION REQUIREMENTS" in content:
        checks.append(("Example & Localization Requirements", True))
    else:
        checks.append(("Example & Localization Requirements", False))
    
    if "locally relevant" in content:
        checks.append(("Localization rules", True))
    else:
        checks.append(("Localization rules", False))
    
    if "tourist packages" in content or "multilingual landing pages" in content:
        checks.append(("Local context examples", True))
    else:
        checks.append(("Local context examples", False))
    
    if "should be treated as low-quality" in content:
        checks.append(("Quality rejection rules", True))
    else:
        checks.append(("Quality rejection rules", False))
    
    for check_name, passed in checks:
        status = "[OK]" if passed else "[ERROR]"
        print(f"   {status} {check_name}")
    
    print()
else:
    print("[ERROR] quality_engine.md not found")
    print()

print("=" * 60)
print("Sanity check complete!")
print("=" * 60)




