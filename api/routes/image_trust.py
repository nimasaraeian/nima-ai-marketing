"""
Image Trust Analysis API Route
==============================

Endpoint for analyzing visual trust level of uploaded images using
the trained visual trust model.

Endpoint: POST /api/analyze/image-trust
"""

import io
from pathlib import Path
from typing import Dict

import tensorflow as tf
from fastapi import APIRouter, File, HTTPException, UploadFile
from tensorflow.keras.applications.efficientnet import preprocess_input
from tensorflow.keras.utils import img_to_array, load_img

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
    """
    global visual_trust_model
    if visual_trust_model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Visual trust model not found at {MODEL_PATH}. "
                "Train the model first with: python training/train_visual_trust_model.py"
            )
        print(f"[IMAGE_TRUST] Loading model from {MODEL_PATH}...")
        visual_trust_model = tf.keras.models.load_model(MODEL_PATH)
        print("[IMAGE_TRUST] Model loaded and cached.")
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


@router.post("/api/analyze/image-trust")
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
        # Read file bytes
        file_bytes = await file.read()
        
        # Validate file is not empty
        if not file_bytes or len(file_bytes) == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty file provided. Please upload a valid image file."
            )
        
        # Validate it's an image
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="File must be an image (jpg, png, etc.)"
            )
        
        # Predict
        result = predict_image(file_bytes)
        
        return {
            "success": True,
            "analysis": result
        }
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except (FileNotFoundError, RuntimeError) as e:
        error_msg = str(e)
        print(f"[ERROR] Visual trust model error: {error_msg}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=503,
            detail=f"Visual trust model not available: {error_msg}"
        )
    except (ValueError, IOError, OSError) as e:
        error_msg = str(e)
        print(f"[ERROR] Image processing error: {error_msg}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image file: {error_msg}"
        )
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"[ERROR] Image trust analysis failed: {error_type}: {error_msg}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Image analysis failed: {error_msg}"
        )

