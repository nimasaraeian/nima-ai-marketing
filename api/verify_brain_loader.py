"""
Verification script for brain_loader.py
Checks all sections are present and in correct order
"""
import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from brain_loader import load_brain_memory, clear_cache
from pathlib import Path

# Clear cache to force reload
clear_cache()

# Load system prompt
prompt = load_brain_memory()

# Expected sections in correct order
expected_sections = [
    'CORE BRAIN',
    'NIMA MEMORY',
    'NIMA MARKETING BRAIN',
    'DOMAIN MEMORY',
    'ACTION MEMORY',
    'ACTION ENGINE',
    'QUALITY ENGINE'
]

print("=" * 60)
print("BRAIN LOADER VERIFICATION")
print("=" * 60)
print()

# Check all sections are present
print("Checking sections:")
print("-" * 60)
found_sections = []
for section in expected_sections:
    section_marker = f'[{section}]'
    if section_marker in prompt:
        found_sections.append(section)
        print(f"✅ Found: [{section}]")
    else:
        print(f"❌ Missing: [{section}]")

print()
print("-" * 60)
print(f"Total sections found: {len(found_sections)}/{len(expected_sections)}")
print()

# Verify order
print("Checking section order:")
print("-" * 60)
all_ordered = True
for i in range(len(expected_sections) - 1):
    current = f'[{expected_sections[i]}]'
    next_section = f'[{expected_sections[i+1]}]'
    current_pos = prompt.find(current)
    next_pos = prompt.find(next_section)
    
    if current_pos != -1 and next_pos != -1:
        if current_pos < next_pos:
            print(f"✅ [{expected_sections[i]}] comes before [{expected_sections[i+1]}]")
        else:
            print(f"❌ Order error: [{expected_sections[i]}] should come before [{expected_sections[i+1]}]")
            all_ordered = False
    else:
        all_ordered = False

print()
print("-" * 60)

# Check file paths
print("Checking file paths:")
print("-" * 60)
project_root = Path(__file__).parent.parent
ai_brain_dir = project_root / "ai_brain"

files = {
    "core_brain": ai_brain_dir / "core_brain.md",
    "memory_nima": ai_brain_dir / "memory_nima.md",
    "marketing_brain": ai_brain_dir / "NIMA_MARKETING_BRAIN.md",
    "memory_domain": ai_brain_dir / "memory_domain.md",
    "memory_actions": ai_brain_dir / "memory_actions.md",
    "action_engine": ai_brain_dir / "action_engine.md",
    "quality_engine": ai_brain_dir / "quality_engine.md"
}

all_files_exist = True
for name, path in files.items():
    exists = path.exists()
    status = "✅" if exists else "❌"
    print(f"{status} {name}: {path.name}")
    if not exists:
        all_files_exist = False

print()
print("=" * 60)
print("VERIFICATION SUMMARY")
print("=" * 60)
print(f"✅ All sections present: {len(found_sections) == len(expected_sections)}")
print(f"✅ Section order correct: {all_ordered}")
print(f"✅ All files exist: {all_files_exist}")
print(f"✅ System prompt size: {len(prompt):,} characters")
print()
print("=" * 60)

if len(found_sections) == len(expected_sections) and all_ordered and all_files_exist:
    print("✅ ALL CHECKS PASSED")
    print("=" * 60)
else:
    print("❌ SOME CHECKS FAILED")
    print("=" * 60)
    exit(1)

