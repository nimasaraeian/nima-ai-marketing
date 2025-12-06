"""
Image Trust Analysis API Route
==============================

Endpoint for analyzing visual trust level of uploaded images using
the trained visual trust model.

Endpoint: POST /api/analyze/image-trust
"""

import io
import logging
import os
import asyncio
from pathlib import Path
from typing import Dict

import tensorflow as tf
from fastapi import APIRouter, File, HTTPException, UploadFile
from tensorflow.keras.applications.efficientnet import preprocess_input
from tensorflow.keras.utils import img_to_array, load_img

# Setup logger
logger = logging.getLogger("image_trust")

# Project root for model path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "visual_trust_model.keras"

# Class names matching the training script
CLASS_NAMES = ["low", "medium", "high"]

# Global lazy loader for the model
visual_trust_model = None


def load_visual_trust_model():
    """
    Lazy load the visual trust model (cached globally after first load).
    
    Returns:
        Loaded Keras model
    
    Raises:
        FileNotFoundError: If model file doesn't exist
        RuntimeError: If model fails to load
    """
    global visual_trust_model
    if visual_trust_model is None:
        # Check if model file exists
        if not MODEL_PATH.exists():
            error_msg = (
                f"Visual trust model not found at {MODEL_PATH}. "
                f"Absolute path: {MODEL_PATH.resolve()}. "
                f"Project root: {PROJECT_ROOT}. "
                "Train the model first with: python training/train_visual_trust_model.py"
            )
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        try:
            logger.info(f"Loading visual trust model from {MODEL_PATH}...")
            logger.info(f"Model file size: {MODEL_PATH.stat().st_size / (1024*1024):.2f} MB")
            visual_trust_model = tf.keras.models.load_model(MODEL_PATH)
            logger.info("Visual trust model loaded and cached successfully")
        except Exception as e:
            error_msg = f"Failed to load visual trust model: {str(e)}"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from e
    
    return visual_trust_model


def predict_image(file_bytes: bytes) -> Dict:
    """
    Predict visual trust level from image bytes.
    
    Args:
        file_bytes: Raw image file bytes
    
    Returns:
        Dictionary with:
            - trust_label: "low" | "medium" | "high"
            - trust_scores: dict mapping class names to probabilities
    
    Raises:
        ValueError: If image cannot be loaded or processed
        RuntimeError: If model prediction fails
    """
    try:
        model = load_visual_trust_model()
    except Exception as e:
        raise RuntimeError(f"Failed to load visual trust model: {str(e)}") from e

    try:
        # Load image from bytes
        img = load_img(
            io.BytesIO(file_bytes),
            target_size=(224, 224)
        )
        arr = img_to_array(img)
        arr = tf.expand_dims(arr, 0)

        # IMPORTANT: apply EfficientNet preprocess
        arr = preprocess_input(arr)

        # Predict
        preds = model.predict(arr, verbose=0)[0]

        # Get predicted label
        label_index = int(tf.argmax(preds))
        if label_index >= len(CLASS_NAMES):
            raise ValueError(f"Invalid prediction index: {label_index}")
        
        trust_label = CLASS_NAMES[label_index]

        # Build trust_scores dictionary
        trust_scores = {
            CLASS_NAMES[i]: float(preds[i])
            for i in range(len(CLASS_NAMES))
        }

        return {
            "trust_label": trust_label,
            "trust_scores": trust_scores
        }
    except Exception as e:
        raise ValueError(f"Failed to process image: {str(e)}") from e


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
    Checks if model is available and can be loaded.
    """
    try:
        # Check if model file exists
        if not MODEL_PATH.exists():
            return {
                "status": "error",
                "message": f"Model file not found at {MODEL_PATH}",
                "model_available": False
            }
        
        # Try to load model (this will cache it)
        try:
            model = load_visual_trust_model()
            return {
                "status": "healthy",
                "message": "Visual trust model is available",
                "model_available": True,
                "model_path": str(MODEL_PATH),
                "model_size_mb": round(MODEL_PATH.stat().st_size / (1024*1024), 2)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Model exists but failed to load: {str(e)}",
                "model_available": False,
                "error_type": type(e).__name__
            }
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "model_available": False
        }


@router.post("")
@router.post("/")
async def analyze_image(file: UploadFile = File(...)):
    """
    Analyze visual trust level of an uploaded image.
    
    Args:
        file: Image file (multipart/form-data)
    
    Returns:
        JSON response with trust analysis:
        {
            "success": true,
            "analysis": {
                "trust_label": "low" | "medium" | "high",
                "trust_scores": {
                    "low": float,
                    "medium": float,
                    "high": float
                }
            }
        }
    """
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
        
        # Log model prediction start
        logger.info("Starting visual trust prediction...")
        
        # Predict (this is the main logic - local TensorFlow model, no external API calls)
        # Run in executor to prevent blocking and handle timeouts on Render
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, predict_image, file_bytes),
                timeout=55.0  # Render timeout is usually 60s, leave 5s buffer
            )
        except asyncio.TimeoutError:
            logger.error("Visual trust prediction timed out (>55s)")
            raise HTTPException(
                status_code=504,
                detail="Image analysis timed out. Please try with a smaller image."
            )
        except RuntimeError as e:
            # Model loading errors
            error_msg = str(e)
            logger.exception(f"Model runtime error: {error_msg}")
            raise HTTPException(
                status_code=503,
                detail="Visual trust model is not available. Please contact support."
            )
        except ValueError as e:
            # Image processing errors
            error_msg = str(e)
            logger.exception(f"Image processing error: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process image: {error_msg}"
            )
        
        # Log successful completion
        trust_label = result.get("trust_label", "unknown")
        logger.info(
            f"Image trust analysis completed successfully: "
            f"trust_label={trust_label}, file_size={file_size} bytes"
        )
        
        return {
            "success": True,
            "analysis": result
        }
        # === YOUR EXISTING LOGIC ENDS HERE ===

    except HTTPException:
        # Re-raise HTTP exceptions as-is (these are intentional client errors)
        raise
    except Exception as e:
        logger.exception("Image trust analysis crashed: %s", e)
        # Return error detail so we can see it from frontend
        raise HTTPException(
            status_code=500,
            detail=f"IMAGE_TRUST_ERROR: {str(e)}",
        )

