"""
Text sanitization utilities for fixing encoding issues.
Production-grade version with multiple repair strategies.
"""
import re
import html

MOJIBAKE_RE = re.compile(r"[Ââ€™""–—·]")

# Build replacements from bytes to avoid encoding issues in source file
REPLACEMENTS = {
    b"\xc2\xb7".decode("latin1"): "\u00b7",      # Â· -> ·
    b"\xc2".decode("latin1"): "",                 # Â -> (empty)
    b"\xc3\xa2\xe2\x80\x99".decode("latin1"): "'",  # â€™ -> '
    b"\xc3\xa2\xe2\x80\x9c".decode("latin1"): '"',  # â€œ -> "
    b"\xc3\xa2\xe2\x80\x9d".decode("latin1"): '"',  # â€ -> "
    b"\xc3\xa2\xe2\x80\x93".decode("latin1"): "-",  # â€" -> -
    b"\xc3\xa2\xe2\x80\x94".decode("latin1"): "\u2014",  # â€" -> —
}


def repair_mojibake(s: str) -> str:
    """
    Fix mojibake where UTF-8 text was mistakenly decoded as Latin-1/CP1252.
    Uses multiple strategies: HTML unescape, direct replacements, and encode/decode fallback.
    
    Args:
        s: Input string that may contain mojibake characters
        
    Returns:
        Fixed string with mojibake repaired, or original if no fix needed
    """
    if not isinstance(s, str) or not s:
        return s

    # 1) HTML entities
    s = html.unescape(s)

    # 2) direct replacements (safe & deterministic)
    for bad, good in REPLACEMENTS.items():
        s = s.replace(bad, good)

    # 3) latin1 → utf8 fallback (best effort)
    try:
        fixed = s.encode("latin1").decode("utf-8")
        if not MOJIBAKE_RE.search(fixed):
            return fixed
    except Exception:
        pass

    return s


def sanitize_any(x):
    """
    Recursively sanitize text in any data structure (dict, list, str, etc.).
    
    Args:
        x: Any object to sanitize
        
    Returns:
        Sanitized object with same structure
    """
    if isinstance(x, str):
        return repair_mojibake(x)
    if isinstance(x, list):
        return [sanitize_any(i) for i in x]
    if isinstance(x, dict):
        return {k: sanitize_any(v) for k, v in x.items()}
    return x
