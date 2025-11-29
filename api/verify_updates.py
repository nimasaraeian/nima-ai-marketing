"""
Sanity check for updated marketing brain files
"""
import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from pathlib import Path
import re

print("=" * 60)
print("SANITY CHECK - Marketing Brain Updates")
print("=" * 60)
print()

# Check NIMA_MARKETING_BRAIN.md
marketing_file = Path("ai_brain/NIMA_MARKETING_BRAIN.md")
if marketing_file.exists():
    content = marketing_file.read_text(encoding='utf-8')
    print(f"[OK] NIMA_MARKETING_BRAIN.md")
    print(f"   Size: {len(content):,} bytes")
    sections = len(re.findall(r'^##', content, re.MULTILINE))
    print(f"   Sections: {sections}")
    
    if "Response Blueprint for Marketing Scenarios" in content:
        print("   [OK] Section 9 (Response Blueprint) found")
    else:
        print("   [ERROR] Section 9 (Response Blueprint) NOT found")
    
    if "Snapshot (Context Summary)" in content:
        print("   [OK] Response Blueprint structure verified")
    
    print()
else:
    print("[ERROR] NIMA_MARKETING_BRAIN.md not found")
    print()

# Check quality_engine.md
quality_file = Path("ai_brain/quality_engine.md")
if quality_file.exists():
    content = quality_file.read_text(encoding='utf-8')
    print(f"[OK] quality_engine.md")
    print(f"   Size: {len(content):,} bytes")
    sections = len(re.findall(r'^##', content, re.MULTILINE))
    print(f"   Sections: {sections}")
    
    if "Marketing Answer Quality Rules" in content:
        print("   [OK] Section 6 (Marketing Answer Quality Rules) found")
    else:
        print("   [ERROR] Section 6 (Marketing Answer Quality Rules) NOT found")
    
    if "REJECTABLE patterns" in content and "REQUIRED elements" in content:
        print("   [OK] Quality rules structure verified")
    
    print()
else:
    print("[ERROR] quality_engine.md not found")
    print()

print("=" * 60)
print("Sanity check complete!")
print("=" * 60)

