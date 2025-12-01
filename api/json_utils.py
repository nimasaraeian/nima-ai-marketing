"""
Safe JSON parsing utilities for handling model responses.

This module provides safe JSON parsing functions that handle cases where
the model might return markdown, bullet points, or other non-JSON text.
"""

import json
from typing import Any, Dict, Optional


def safe_parse_json(raw: str, context: str = "model response") -> Dict[str, Any]:
    """
    Safely parse JSON from model output, handling common edge cases.
    
    Args:
        raw: Raw string output from the model
        context: Context string for error messages (e.g., "cognitive friction analysis")
    
    Returns:
        Parsed JSON object as dictionary
    
    Raises:
        ValueError: If the string is clearly not JSON or parsing fails
        json.JSONDecodeError: If JSON parsing fails after validation
    """
    if not raw:
        raise ValueError(f"Empty {context} received. Expected JSON object.")
    
    # Trim whitespace
    trimmed = raw.strip()
    
    # Check if it looks like JSON (should start with { or [)
    if not trimmed.startswith("{") and not trimmed.startswith("["):
        # Log the problematic output for debugging
        preview = trimmed[:200] if len(trimmed) > 200 else trimmed
        raise ValueError(
            f"{context} is not valid JSON. "
            f"Expected JSON object or array, but got text starting with: {repr(preview[:50])}"
        )
    
    # Try to extract JSON if it's wrapped in markdown code blocks
    if "```json" in trimmed:
        # Extract content between ```json and ```
        start = trimmed.find("```json") + 7
        end = trimmed.find("```", start)
        if end != -1:
            trimmed = trimmed[start:end].strip()
    elif "```" in trimmed:
        # Extract content between ``` and ```
        start = trimmed.find("```") + 3
        end = trimmed.find("```", start)
        if end != -1:
            trimmed = trimmed[start:end].strip()
    
    # Try to find JSON object boundaries if there's extra text
    if trimmed.startswith("{"):
        # Find the matching closing brace
        brace_count = 0
        json_end = -1
        for i, char in enumerate(trimmed):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break
        if json_end > 0:
            trimmed = trimmed[:json_end]
    
    # Final parse attempt
    try:
        return json.loads(trimmed)
    except json.JSONDecodeError as e:
        # Log the problematic output for debugging
        preview = trimmed[:500] if len(trimmed) > 500 else trimmed
        error_msg = (
            f"Failed to parse {context} as JSON. "
            f"Error: {str(e)}. "
            f"Raw output preview: {repr(preview)}"
        )
        print(f"⚠️ {error_msg}")
        raise ValueError(error_msg) from e

