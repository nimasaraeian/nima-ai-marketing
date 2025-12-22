"""
Element Detection Service using OpenAI Vision API.
Detects UI elements (CTA, headline, pricing, etc.) with bounding boxes.
"""
import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Literal
from PIL import Image

from api.chat import get_client

# Element types supported
ElementType = Literal["cta", "headline", "pricing", "testimonial", "badge", "logo", "nav", "form", "input"]

# System prompt for element detection
ELEMENT_DETECTION_PROMPT = """You are a UI element detector. Analyze the screenshot and return a JSON array of detected UI elements.

For each element, provide:
- id: unique identifier (e.g., "cta_1", "headline_1")
- type: one of: "cta", "headline", "pricing", "testimonial", "badge", "logo", "nav", "form", "input"
- text: the visible text content (or null if not applicable)
- bbox: [x, y, width, height] in pixel coordinates (top-left origin)
- confidence: 0.0 to 1.0

Rules:
- Only detect elements that are clearly visible above the fold
- bbox coordinates must be accurate pixel positions
- Focus on marketing-critical elements (CTAs, headlines, pricing, trust signals)
- Return empty array if no elements detected

Return JSON only, no markdown, no explanations."""


def get_image_dimensions(image_path: str) -> Tuple[int, int]:
    """Get image width and height."""
    try:
        with Image.open(image_path) as img:
            return img.size  # Returns (width, height)
    except Exception as e:
        print(f"Error getting image dimensions: {e}")
        return (1365, 768)  # Default desktop viewport


async def detect_elements_in_screenshot(
    screenshot_path: str,
    viewport: Literal["desktop", "mobile"] = "desktop"
) -> Dict[str, Any]:
    """
    Detect UI elements in a screenshot using OpenAI Vision API.
    
    Args:
        screenshot_path: Path to screenshot image file
        viewport: "desktop" or "mobile"
        
    Returns:
        {
            "viewport": "desktop"|"mobile",
            "image_size": [width, height],
            "detected_elements": [
                {
                    "id": "cta_1",
                    "type": "cta",
                    "text": "Sign Up Now",
                    "bbox": [x, y, w, h],
                    "confidence": 0.9
                },
                ...
            ]
        }
    """
    try:
        # Check if screenshot exists
        if not os.path.exists(screenshot_path):
            return {
                "viewport": viewport,
                "image_size": [1365, 768] if viewport == "desktop" else [390, 844],
                "detected_elements": []
            }
        
        # Get image dimensions
        img_width, img_height = get_image_dimensions(screenshot_path)
        
        # Read image and encode to base64
        with open(screenshot_path, "rb") as f:
            image_data = f.read()
        
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        mime_type = "image/png"  # Screenshots are PNG
        
        # Call OpenAI Vision API
        client = get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": ELEMENT_DETECTION_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Detect UI elements in this screenshot. Return JSON array only."},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}},
                    ],
                },
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        
        raw_json = response.choices[0].message.content or "[]"
        
        # Extract JSON (handle markdown code blocks if present)
        if "```json" in raw_json:
            raw_json = raw_json.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_json:
            raw_json = raw_json.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        try:
            elements_data = json.loads(raw_json)
            if not isinstance(elements_data, list):
                elements_data = []
        except json.JSONDecodeError as e:
            print(f"Error parsing vision API JSON: {e}")
            print(f"Raw response: {raw_json[:500]}")
            elements_data = []
        
        # Normalize elements to schema
        detected_elements = []
        for idx, elem in enumerate(elements_data):
            try:
                # Validate and normalize element
                elem_id = elem.get("id") or f"element_{idx + 1}"
                elem_type = elem.get("type", "input")
                
                # Validate type
                valid_types = ["cta", "headline", "pricing", "testimonial", "badge", "logo", "nav", "form", "input"]
                if elem_type not in valid_types:
                    elem_type = "input"  # Default fallback
                
                # Get bbox and validate
                bbox_raw = elem.get("bbox", [])
                if isinstance(bbox_raw, list) and len(bbox_raw) >= 4:
                    bbox = [int(bbox_raw[0]), int(bbox_raw[1]), int(bbox_raw[2]), int(bbox_raw[3])]
                    # Ensure bbox is within image bounds
                    bbox[0] = max(0, min(bbox[0], img_width))
                    bbox[1] = max(0, min(bbox[1], img_height))
                    bbox[2] = max(1, min(bbox[2], img_width - bbox[0]))
                    bbox[3] = max(1, min(bbox[3], img_height - bbox[1]))
                else:
                    bbox = [0, 0, 100, 50]  # Default small box
                
                # Get text
                text = elem.get("text")
                if text and not isinstance(text, str):
                    text = str(text)
                elif not text:
                    text = None
                
                # Get confidence
                confidence = float(elem.get("confidence", 0.5))
                confidence = max(0.0, min(1.0, confidence))
                
                detected_elements.append({
                    "id": elem_id,
                    "type": elem_type,
                    "text": text,
                    "bbox": bbox,
                    "confidence": confidence
                })
            except Exception as e:
                print(f"Error normalizing element {idx}: {e}")
                continue
        
        return {
            "viewport": viewport,
            "image_size": [img_width, img_height],
            "detected_elements": detected_elements
        }
        
    except Exception as e:
        print(f"Error in detect_elements_in_screenshot: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
        # Return empty evidence on error
        return {
            "viewport": viewport,
            "image_size": [1365, 768] if viewport == "desktop" else [390, 844],
            "detected_elements": []
        }


