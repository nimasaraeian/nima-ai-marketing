"""
Text utility functions for fixing encoding issues and text processing.
"""


def fix_mojibake(s: str) -> str:
    """
    Fix common mojibake issues (UTF-8 decoded as cp1252/latin1).
    
    Args:
        s: Input string that may contain mojibake characters
        
    Returns:
        Fixed string with mojibake characters replaced
    """
    if not s:
        return s
    
    # Common mojibake fixes (UTF-8 decoded as cp1252/latin1)
    # Using bytes to avoid encoding issues in source file
    replacements = {
        b"\xc2\xb7".decode("latin1"): "\u00b7",  # middle dot
        b"\xc2\xa0".decode("latin1"): " ",       # non-breaking space (as regular space)
        b"\xe2\x80\x99".decode("latin1"): "'",   # right single quotation mark
        b"\xe2\x80\x9c".decode("latin1"): "\u201c",  # left double quotation mark
        b"\xe2\x80\x9d".decode("latin1"): "\u201d",  # right double quotation mark
        b"\xe2\x80\x93".decode("latin1"): "\u2013",  # en dash
        b"\xe2\x80\x94".decode("latin1"): "\u2014",  # em dash
        b"\xe2\x80\xa6".decode("latin1"): "\u2026",  # horizontal ellipsis
        b"\xe2\x80\xa2".decode("latin1"): "\u2022",  # bullet
        b"\xe2\x88\x92".decode("latin1"): "\u2212",  # minus sign
        b"\xe2".decode("latin1"): "\u2013",          # Last resort; optional (can be too aggressive)
    }
    
    for bad, good in replacements.items():
        s = s.replace(bad, good)
    
    return s
