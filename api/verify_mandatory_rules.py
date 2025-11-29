"""
Sanity check for mandatory example and localization rules
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
print("SANITY CHECK - Mandatory Example & Localization Rules")
print("=" * 60)
print()

# Check NIMA_MARKETING_BRAIN.md
marketing_file = Path("ai_brain/NIMA_MARKETING_BRAIN.md")
if marketing_file.exists():
    content = marketing_file.read_text(encoding='utf-8')
    print("[OK] NIMA_MARKETING_BRAIN.md")
    print(f"   Size: {len(content):,} bytes")
    sections = len(re.findall(r'^##', content, re.MULTILINE))
    print(f"   Sections: {sections}")
    
    checks = []
    if "Mandatory Example Generation Rules" in content:
        checks.append(("Section 10 (Mandatory Example Generation Rules)", True))
    else:
        checks.append(("Section 10 (Mandatory Example Generation Rules)", False))
    
    if "Headline Example:" in content:
        checks.append(("Mandatory format (Headline Example)", True))
    else:
        checks.append(("Mandatory format (Headline Example)", False))
    
    if "Istanbul-specific hooks" in content:
        checks.append(("Istanbul-specific hooks", True))
    else:
        checks.append(("Istanbul-specific hooks", False))
    
    if "tourists vs locals" in content:
        checks.append(("Tourist vs local context", True))
    else:
        checks.append(("Tourist vs local context", False))
    
    if "Top-rated aesthetic clinic near Taksim" in content:
        checks.append(("Localized ad angle examples", True))
    else:
        checks.append(("Localized ad angle examples", False))
    
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
    sections = len(re.findall(r'^##', content, re.MULTILINE))
    print(f"   Sections: {sections}")
    
    checks = []
    if "Example Enforcement Rules" in content:
        checks.append(("Example Enforcement Rules", True))
    else:
        checks.append(("Example Enforcement Rules", False))
    
    if "Localization Enforcement Rules" in content:
        checks.append(("Localization Enforcement Rules", True))
    else:
        checks.append(("Localization Enforcement Rules", False))
    
    if "Did I give headlines?" in content:
        checks.append(("Internal check questions", True))
    else:
        checks.append(("Internal check questions", False))
    
    if "automatically LOW QUALITY" in content:
        checks.append(("Quality rejection rules", True))
    else:
        checks.append(("Quality rejection rules", False))
    
    if "MUST revise before responding" in content:
        checks.append(("Revision requirement", True))
    else:
        checks.append(("Revision requirement", False))
    
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




