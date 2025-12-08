"""
Image Trust Analysis API Route
==============================

Endpoint for analyzing visual trust level of uploaded images using
the trained visual trust model.

Endpoint: POST /api/analyze/image-trust
"""

import json
import logging
import os
import base64
from pathlib import Path
from typing import Dict, Any, Literal, Optional, List

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
# TensorFlow imports removed - we now use OpenAI Vision API exclusively

# Import models and OpenAI client from cognitive_friction_engine
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from cognitive_friction_engine import (
    VisualTrustResult, 
    VisualElement, 
    VISUAL_TRUST_SYSTEM_PROMPT,
    get_client
)

# Setup logger
logger = logging.getLogger("image_trust")

# LEGACY TensorFlow model constants - NO LONGER USED
# We now use OpenAI Vision API exclusively
# PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
# MODEL_PATH = PROJECT_ROOT / "models" / "visual_trust_model.keras"
# CLASS_NAMES = ["low", "medium", "high"]
# visual_trust_model = None


# LEGACY FUNCTION REMOVED - No longer using TensorFlow model fallback
# This function returned old format with trust_label/trust_scores
# def build_visual_trust_fallback() -> Dict[str, Any]:
#     """LEGACY - DO NOT USE"""
#     pass


# LEGACY FUNCTION REMOVED - No longer converting from old trust_label/trust_scores format
# def build_visual_trust_result(...):
#     """LEGACY - DO NOT USE"""
#     pass


# LEGACY TENSORFLOW MODEL FUNCTIONS - NO LONGER USED
# We now use OpenAI Vision API exclusively for visual trust analysis
# def load_visual_trust_model():
#     """LEGACY - DO NOT USE - TensorFlow model loader"""
#     pass

# def predict_image(file_bytes: bytes) -> Dict:
#     """LEGACY - DO NOT USE - TensorFlow model predictor"""
#     pass


# Create router
router = APIRouter()


@router.get("/")
async def image_trust_root():
    """Root endpoint for image trust service."""
    return {
        "service": "image-trust",
        "status": "active",
        "endpoints": {
            "health": "/api/analyze/image-trust/health",
            "analyze": "/api/analyze/image-trust"
        }
    }


@router.get("/health")
async def image_trust_health():
    """
    Health check endpoint for image trust service.
    Now checks OpenAI API availability instead of TensorFlow model.
    """
    try:
        # Check OpenAI API key availability
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                "status": "error",
                "message": "OPENAI_API_KEY not set",
                "model_available": False,
                "service_type": "vision_api"
            }
        
        # Try to get OpenAI client (this validates the API key)
        try:
            client = get_client()
            return {
                "status": "healthy",
                "message": "Visual trust service using OpenAI Vision API is available",
                "model_available": True,
                "service_type": "vision_api",
                "model": "gpt-4o-mini"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"OpenAI client initialization failed: {str(e)}",
                "model_available": False,
                "error_type": type(e).__name__,
                "service_type": "vision_api"
            }
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "model_available": False,
            "service_type": "vision_api"
        }


@router.post("")
@router.post("/")
async def analyze_image(file: UploadFile = File(...)):
    """
    Analyze visual trust level of an uploaded image using OpenAI Vision API.
    
    This endpoint EXCLUSIVELY uses OpenAI Vision API and returns VisualTrustResult
    with elements and narrative. It NEVER returns the old trust_label/trust_scores format.
    
    Args:
        file: Image file (multipart/form-data)
    
    Returns:
        JSON response with visual trust analysis:
        {
            "success": true,
            "analysis": {
                "status": "ok" | "fallback" | "unavailable",
                "label": "Low" | "Medium" | "High" | null,
                "overall_score": number | null,
                "distribution": {"low": number, "medium": number, "high": number} | null,
                "notes": string | null,
                "elements": [
                    {
                        "id": string,
                        "role": "headline" | "primary_cta" | ...,
                        "approx_position": "top-center" | ...,
                        "text": string | null,
                        "visual_cues": string[],
                        "analysis": {...}
                    }
                ],
                "narrative": string[]
            }
        }
    """
    # 🔥 CRITICAL: This endpoint ONLY uses Vision API. No legacy TensorFlow model.
    logger.warning("🔥 USING VISION-BASED IMAGE ANALYSIS 🔥")
    
    try:
        logger.info(
            "Image trust request received: filename=%s content_type=%s",
            file.filename,
            file.content_type,
        )

        # === YOUR EXISTING LOGIC STARTS HERE ===
        # Log incoming request details
        filename = file.filename or "unknown"
        content_type = file.content_type or "unknown"
        logger.info(
            f"Received image for trust analysis: filename={filename}, "
            f"content_type={content_type}"
        )
        
        # Log environment variables used (names only, not values)
        env_vars_used = []
        # Check if any environment variables are used in this module
        # (Currently this endpoint doesn't use env vars, but log if any are checked)
        if os.getenv("OPENAI_API_KEY"):
            env_vars_used.append("OPENAI_API_KEY")
        if os.getenv("TENSORFLOW_LOGGING_LEVEL"):
            env_vars_used.append("TENSORFLOW_LOGGING_LEVEL")
        if env_vars_used:
            logger.info(f"Environment variables accessed: {', '.join(env_vars_used)}")
        
        # Read file bytes
        file_bytes = await file.read()
        file_size = len(file_bytes)
        logger.info(f"Image file size: {file_size} bytes")
        
        # Validate file is not empty
        if not file_bytes or file_size == 0:
            logger.warning("Empty file provided")
            raise HTTPException(
                status_code=400,
                detail="Empty file provided. Please upload a valid image file."
            )
        
        # Validate file size (max 10MB to prevent memory issues on Render)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        if file_size > MAX_FILE_SIZE:
            logger.warning(f"File too large: {file_size} bytes (max: {MAX_FILE_SIZE})")
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Validate it's an image
        if not content_type.startswith("image/"):
            logger.warning(f"Invalid content type: {content_type}")
            raise HTTPException(
                status_code=400,
                detail="File must be an image (jpg, png, etc.)"
            )
        
        # 🔥 USING VISION-BASED IMAGE ANALYSIS 🔥
        logger.warning("🔥 USING VISION-BASED IMAGE ANALYSIS 🔥")
        logger.info("Starting Vision API visual trust analysis...")
        
        # Use OpenAI Vision API for detailed element-by-element analysis
        try:
            # Encode image to base64
            image_b64 = base64.b64encode(file_bytes).decode("utf-8")
            mime_type = content_type or "image/png"
            data_url = f"data:{mime_type};base64,{image_b64}"
            
            # Get OpenAI client (reuse existing pattern from cognitive_friction_engine)
            client = get_client()
            
            # Call Vision API
            logger.info("Calling OpenAI Vision API for visual trust analysis...")
            logger.info(f"Image size: {file_size} bytes, MIME type: {mime_type}")
            
            # Ensure correct message format with both text and image
            user_message_content = [
                {"type": "text", "text": "Analyze this landing page screenshot."},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": data_url
                    },
                },
            ]
            
            logger.debug(f"User message content structure: text + image_url with data URL (length: {len(data_url)} chars)")
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": VISUAL_TRUST_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": user_message_content,
                    },
                ],
                temperature=0.2,
                max_tokens=3000,  # Increased to ensure we get enough elements and narrative
            )
            
            # Parse response
            raw_content = response.choices[0].message.content
            logger.info(f"[DEBUG] Vision API raw response (first 500 chars): {raw_content[:500]}")
            logger.info(f"[DEBUG] Vision API raw response length: {len(raw_content)} chars")
            
            # Extract JSON (handle markdown code blocks if present)
            raw_json = raw_content
            if "```json" in raw_json:
                logger.debug("Found ```json markdown block, extracting JSON...")
                raw_json = raw_json.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_json:
                logger.debug("Found ``` markdown block, extracting JSON...")
                raw_json = raw_json.split("```")[1].split("```")[0].strip()
            
            logger.info(f"[DEBUG] Extracted JSON (first 500 chars): {raw_json[:500]}")
            
            # Parse JSON with error handling
            try:
                data = json.loads(raw_json)
                logger.info(f"[DEBUG] Successfully parsed JSON. Keys: {list(data.keys())}")
            except json.JSONDecodeError as json_err:
                logger.error(f"[DEBUG] JSON parsing failed! Error: {json_err}")
                logger.error(f"[DEBUG] Raw JSON that failed to parse (first 1000 chars): {raw_json[:1000]}")
                raise json_err
            
            # Convert to VisualTrustResult + VisualElement list
            elements = []
            raw_elements = data.get("elements", [])
            logger.info(f"[DEBUG] Found {len(raw_elements)} raw elements in response")
            
            for idx, e in enumerate(raw_elements):
                try:
                    element = VisualElement(
                        id=e.get("id", f"element_{len(elements)}"),
                        role=e.get("role", "other"),
                        approx_position=e.get("approx_position", "middle-center"),
                        text=e.get("text"),
                        visual_cues=e.get("visual_cues") or [],
                        analysis=e.get("analysis") or {},
                    )
                    elements.append(element)
                    logger.debug(f"[DEBUG] Successfully parsed element {idx+1}: {element.id} ({element.role})")
                except Exception as elem_err:
                    logger.warning(f"[DEBUG] Failed to parse element {idx+1}: {e}, error: {elem_err}")
                    continue
            
            overall = data.get("overall_visual_trust") or {}
            narrative = data.get("narrative") or []
            
            logger.info(f"[DEBUG] Parsed {len(elements)} elements, {len(narrative)} narrative items")
            logger.info(f"[DEBUG] Overall trust data: {overall}")
            
            # Validate minimum requirements
            if len(elements) < 3:
                logger.warning(
                    f"[DEBUG] Insufficient elements: got {len(elements)}, expected at least 3. "
                    f"Raw elements: {raw_elements}"
                )
                # Don't fail, but log the issue
            
            if len(narrative) < 2:
                logger.warning(
                    f"[DEBUG] Insufficient narrative: got {len(narrative)}, expected at least 2. "
                    f"Raw narrative: {narrative}"
                )
                # Don't fail, but log the issue
            
            # Normalize label
            label_raw = overall.get("label", "").strip()
            label: Optional[Literal["Low", "Medium", "High"]] = None
            if label_raw:
                label_lower = label_raw.lower()
                if "low" in label_lower:
                    label = "Low"
                elif "medium" in label_lower:
                    label = "Medium"
                elif "high" in label_lower:
                    label = "High"
            
            overall_score = overall.get("score")
            if overall_score is not None:
                overall_score = float(overall_score)
                # Clamp to 0-100
                overall_score = max(0.0, min(100.0, overall_score))
            
            # Determine status based on data quality
            # CRITICAL: If elements is empty, we MUST NOT return status="ok"
            status = "ok"
            notes = None
            
            if len(elements) == 0:
                # Empty elements means the vision pipeline is broken
                status = "fallback"
                notes = (
                    "Visual structure analysis returned no elements. "
                    "The vision pipeline may be broken. This is a fallback response."
                )
                logger.error(f"[DEBUG] CRITICAL: Empty elements array! Setting status to 'fallback'")
                logger.error(f"[DEBUG] Raw elements from API: {raw_elements}")
            elif len(elements) < 3 or len(narrative) < 2:
                status = "fallback"
                notes = (
                    f"Visual structure analysis returned insufficient data "
                    f"(elements: {len(elements)}, narrative: {len(narrative)}). "
                    f"This is a partial result."
                )
                logger.warning(f"[DEBUG] Setting status to 'fallback' due to insufficient data")
            
            result = VisualTrustResult(
                status=status,
                label=label,
                overall_score=overall_score,
                distribution=None,  # Can be calculated later if needed
                notes=notes,
                elements=elements,
                narrative=narrative,
            )
            
            # Final validation: if status is "ok", elements must not be empty
            if result.status == "ok" and len(result.elements) == 0:
                logger.error("[DEBUG] CRITICAL INVARIANT VIOLATION: status='ok' but elements is empty!")
                result.status = "fallback"
                result.notes = "Visual structure analysis returned empty elements. This is a fallback response."
                result.narrative = [
                    "Visual structure analysis could not extract elements from the image.",
                    "This is a heuristic fallback response."
                ]
            
            logger.info(
                f"Vision API analysis completed: status={status}, label={label}, score={overall_score}, "
                f"elements={len(elements)}, narrative_items={len(narrative)}"
            )
            
            # CRITICAL: Validate response format - must NEVER contain trust_label or trust_scores
            result_dict = result.dict()
            if "trust_label" in result_dict or "trust_scores" in result_dict:
                logger.error("[DEBUG] CRITICAL: Response contains old format keys! This should never happen.")
                raise ValueError("Response contains legacy trust_label/trust_scores keys")
            
            # Return in correct format - VisualTrustResult with elements and narrative
            logger.info(f"[DEBUG] Returning response with status={result_dict.get('status')}, elements={len(result_dict.get('elements', []))}, narrative={len(result_dict.get('narrative', []))}")
            return {
                "success": True,
                "analysis": result_dict
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"[DEBUG] JSON parsing failed with error: {e}")
            logger.error(f"[DEBUG] Error at position {e.pos if hasattr(e, 'pos') else 'unknown'}")
            logger.error(f"[DEBUG] Raw content that failed (first 1000 chars): {raw_content[:1000] if 'raw_content' in locals() else 'N/A'}")
            # Fallback instead of 500
            fallback = VisualTrustResult(
                status="fallback",
                label="Medium",
                overall_score=60.0,
                distribution={"low": 0.3, "medium": 0.5, "high": 0.2},
                notes="Visual structure analysis could not be fully parsed. This is a heuristic fallback.",
                elements=[],
                narrative=[
                    "Visual structure analysis could not be fully parsed. This is a heuristic fallback.",
                    "The AI vision model response was not in the expected JSON format."
                ],
            )
            return {
                "success": True,
                "analysis": fallback.dict()
            }
        except ValueError as e:
            # Image processing errors
            error_msg = str(e)
            logger.exception(f"Image processing error: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process image: {error_msg}"
            )
        except Exception as e:
            # Any other error - return fallback instead of 500
            logger.exception(f"[DEBUG] Vision API visual trust analysis failed: {e}")
            logger.error(f"[DEBUG] Exception type: {type(e).__name__}")
            logger.error(f"[DEBUG] Exception details: {str(e)}")
            import traceback
            logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
            fallback = VisualTrustResult(
                status="fallback",
                label="Medium",
                overall_score=60.0,
                distribution={"low": 0.3, "medium": 0.5, "high": 0.2},
                notes=f"Visual structure analysis could not be fully parsed. Error: {str(e)}. This is a heuristic fallback.",
                elements=[],
                narrative=[
                    "Visual structure analysis could not be fully parsed. This is a heuristic fallback.",
                    f"The AI vision model encountered an error: {type(e).__name__}"
                ],
            )
            return {
                "success": True,
                "analysis": fallback.dict()
            }
        # === YOUR EXISTING LOGIC ENDS HERE ===

    except HTTPException:
        # Re-raise HTTP exceptions as-is (these are intentional client errors)
        raise
    except Exception as e:
        # CRITICAL: Never return old format. Always return VisualTrustResult
        logger.exception("Image trust analysis crashed: %s", e)
        logger.error(f"[DEBUG] Top-level exception handler caught: {type(e).__name__}: {str(e)}")
        # Return fallback VisualTrustResult instead of raising 500
        fallback = VisualTrustResult(
            status="fallback",
            label="Medium",
            overall_score=60.0,
            distribution={"low": 0.3, "medium": 0.5, "high": 0.2},
            notes=f"Visual trust analysis encountered an unexpected error: {str(e)}. This is a fallback response.",
            elements=[],
            narrative=[
                "Visual structure analysis could not be completed due to an unexpected error.",
                f"Error type: {type(e).__name__}"
            ],
        )
        return {
            "success": True,
            "analysis": fallback.dict()
        }


@router.post("/vision")
@router.post("/vision/")
async def analyze_image_trust_vision(file: UploadFile = File(...)) -> VisualTrustResult:
    """
    Analyze visual trust using OpenAI Vision API (GPT-4o-mini with vision).
    
    This endpoint provides detailed element-by-element analysis of landing pages,
    detecting logos, headlines, CTAs, trust badges, etc., and their impact on trust.
    
    Args:
        file: Image file (multipart/form-data)
    
    Returns:
        VisualTrustResult with elements and narrative
    """
    try:
        logger.info(
            "Vision API image trust request received: filename=%s content_type=%s",
            file.filename,
            file.content_type,
        )
        
        # Read and encode image
        content = await file.read()
        if not content or len(content) == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty file provided. Please upload a valid image file."
            )
        
        # Determine MIME type
        mime_type = file.content_type or "image/png"
        if not mime_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="File must be an image (jpg, png, etc.)"
            )
        
        # Encode to base64
        image_b64 = base64.b64encode(content).decode("utf-8")
        data_url = f"data:{mime_type};base64,{image_b64}"
        
        # Get OpenAI client
        client = get_client()
        
        # Call Vision API
        logger.info("Calling OpenAI Vision API for visual trust analysis...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": VISUAL_TRUST_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this landing page screenshot."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_url
                            },
                        },
                    ],
                },
            ],
            temperature=0.2,
            max_tokens=2000,
        )
        
        # Parse response
        raw_json = response.choices[0].message.content
        logger.debug(f"Vision API raw response: {raw_json[:200]}...")
        
        # Extract JSON (handle markdown code blocks if present)
        if "```json" in raw_json:
            raw_json = raw_json.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_json:
            raw_json = raw_json.split("```")[1].split("```")[0].strip()
        
        data = json.loads(raw_json)
        
        # Convert to VisualTrustResult + VisualElement
        elements = []
        for e in data.get("elements", []):
            try:
                element = VisualElement(
                    id=e.get("id", f"element_{len(elements)}"),
                    role=e.get("role", "other"),
                    approx_position=e.get("approx_position", "middle-center"),
                    text=e.get("text"),
                    visual_cues=e.get("visual_cues") or [],
                    analysis=e.get("analysis") or {},
                )
                elements.append(element)
            except Exception as elem_err:
                logger.warning(f"Failed to parse element: {e}, error: {elem_err}")
                continue
        
        overall = data.get("overall_visual_trust") or {}
        narrative = data.get("narrative") or []
        
        # Normalize label
        label_raw = overall.get("label", "").strip()
        label: Optional[Literal["Low", "Medium", "High"]] = None
        if label_raw:
            label_lower = label_raw.lower()
            if "low" in label_lower:
                label = "Low"
            elif "medium" in label_lower:
                label = "Medium"
            elif "high" in label_lower:
                label = "High"
        
        overall_score = overall.get("score")
        if overall_score is not None:
            overall_score = float(overall_score)
            # Clamp to 0-100
            overall_score = max(0.0, min(100.0, overall_score))
        
        result = VisualTrustResult(
            status="ok",
            label=label,
            overall_score=overall_score,
            distribution=None,  # Can be calculated later if needed
            notes=None,
            elements=elements,
            narrative=narrative,
        )
        
        logger.info(
            f"Vision API analysis completed: label={label}, score={overall_score}, "
            f"elements={len(elements)}, narrative_items={len(narrative)}"
        )
        
        return result
        
    except json.JSONDecodeError as e:
        logger.exception(f"Failed to parse Vision API JSON response: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse AI response. Raw response: {raw_json[:200]}..."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Vision API visual trust analysis failed: {e}")
        # Return fallback result instead of raising 500
        return VisualTrustResult(
            status="fallback",
            notes=f"Vision API analysis failed: {str(e)}. Using fallback estimation.",
            elements=[],
            narrative=[]
        )

