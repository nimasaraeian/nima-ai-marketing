"""
Verify system prompt includes all mandatory rules
"""
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from brain_loader import load_brain_memory, clear_cache

clear_cache()
prompt = load_brain_memory()

print("=" * 60)
print("SYSTEM PROMPT VERIFICATION")
print("=" * 60)
print()
print(f"System prompt size: {len(prompt):,} characters")
print()

checks = [
    ("Mandatory Example Generation Rules", "Mandatory Example Generation Rules" in prompt),
    ("Headline Example format", "Headline Example:" in prompt),
    ("Hook Idea format", "Hook Idea:" in prompt),
    ("Istanbul-specific hooks", "Istanbul-specific hooks" in prompt),
    ("Tourist vs locals", "tourists vs locals" in prompt),
    ("Localized ad angles", "Top-rated aesthetic clinic near Taksim" in prompt),
    ("Example Enforcement Rules", "Example Enforcement Rules" in prompt),
    ("Localization Enforcement Rules", "Localization Enforcement Rules" in prompt),
    ("Internal check questions", "Did I give headlines?" in prompt),
    ("Revision requirement", "MUST revise before responding" in prompt),
]

print("Content verification:")
print("-" * 60)
all_passed = True
for name, passed in checks:
    status = "[OK]" if passed else "[ERROR]"
    print(f"  {status} {name}")
    if not passed:
        all_passed = False

print()
print("=" * 60)
if all_passed:
    print("[OK] All mandatory rules integrated in system prompt!")
    print("=" * 60)
    print()
    print("Note: API quota exceeded - cannot run live test.")
    print("But system prompt is ready with all new rules.")
else:
    print("[ERROR] Some rules missing from system prompt!")
    print("=" * 60)




