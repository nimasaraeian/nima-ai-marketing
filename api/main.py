"""
FastAPI application with AI brain system prompt - Main entry point

Deployment:
  For Render or similar services, use:
  uvicorn api.main:app --host 0.0.0.0 --port $PORT
  
  Module path: api.main:app
"""
from fastapi import APIRouter, FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import sys
import base64
import json
import logging
import io
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import uuid4
from PIL import Image
import numpy as np

# Add api directory to path for imports
api_dir = Path(__file__).parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

# Ensure stdout/stderr can emit Unicode characters (e.g., checkmarks) on Windows consoles
if os.name == "nt":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        # If reconfigure isn't supported, fall back silently without crashing startup
        pass

from brain_loader import load_brain_memory
from chat import chat_completion, chat_completion_with_image
from cognitive_friction_engine import (
    analyze_cognitive_friction,
    CognitiveFrictionInput,
    CognitiveFrictionResult,
    InvalidAIResponseError,
    VisualTrustAnalysis,
)
from psychology_engine import (
    analyze_psychology,
    analyze_advanced_psychology,
    PsychologyAnalysisInput,
    PsychologyAnalysisResult
)
from rewrite_engine import rewrite_text
from models.rewrite_models import RewriteInput, RewriteOutput
from visual_trust_engine import analyze_visual_trust_from_path
from api.routes.image_trust import router as image_trust_router
from api.routes.training_landing_friction import router as landing_friction_training_router

# Load environment variables
# Try loading from project root .env file
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
else:
    load_dotenv()

PSYCHOLOGY_FINE_TUNE_MODEL_PATH = (
    project_root / "data" / "psychology_training" / "fine_tune" / "last_model.json"
)


def load_psychology_finetune_model_id() -> str:
    """
    Read the last fine-tuned psychology model id from disk.
    """
    if not PSYCHOLOGY_FINE_TUNE_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Fine-tuned model metadata not found at {PSYCHOLOGY_FINE_TUNE_MODEL_PATH}"
        )

    try:
        raw_data = PSYCHOLOGY_FINE_TUNE_MODEL_PATH.read_text(encoding="utf-8")
        metadata = json.loads(raw_data)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {PSYCHOLOGY_FINE_TUNE_MODEL_PATH}: {exc}"
        ) from exc
    except OSError as exc:
        raise ValueError(
            f"Unable to read {PSYCHOLOGY_FINE_TUNE_MODEL_PATH}: {exc}"
        ) from exc

    model_id = None
    if isinstance(metadata, dict):
        model_id = metadata.get("model_id") or metadata.get("model") or metadata.get(
            "fine_tuned_model"
        )
    elif isinstance(metadata, str):
        model_id = metadata.strip()

    if not model_id:
        raise ValueError(
            f"No model id found inside {PSYCHOLOGY_FINE_TUNE_MODEL_PATH}. "
            "Ensure the fine-tune job metadata is saved correctly."
        )
    return model_id

# Initialize FastAPI app
app = FastAPI(title="Nima AI Brain API", version="1.0.0")

# Add CORS middleware
# Production: allow frontend domains
# Development: allow localhost for local testing
origins = [
    "https://nimasaraeian.com",
    "https://www.nimasaraeian.com",
    "https://nima-ai-marketing.onrender.com",  # Render deployment
    "http://localhost:3000",  # DEV: local development
    "http://127.0.0.1:3000",  # DEV: local development
    "http://localhost:8000",  # DEV: local development
    "http://127.0.0.1:8000",  # DEV: local development
    "http://localhost:8080",  # DEV: local frontend server
    "http://127.0.0.1:8080",  # DEV: local frontend server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler to catch any unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to prevent 500 errors from leaking to clients.
    Returns a proper JSON response instead of letting FastAPI raise HTTPException.
    """
    import logging
    logger = logging.getLogger("brain")
    
    error_type = type(exc).__name__
    error_message = str(exc)
    
    logger.error(f"Global exception handler caught: {error_type}: {exc}", exc_info=True)
    print(f"\n❌ GLOBAL EXCEPTION HANDLER: {error_type}: {exc}")
    import traceback
    traceback.print_exc()
    
    # For HTTPExceptions, re-raise them (they're intentional)
    if isinstance(exc, HTTPException):
        raise exc
    
    # For other exceptions, return a BrainResponse to maintain API contract
    user_friendly_message = "An unexpected error occurred. Please try again later."
    
    if "OPENAI_API_KEY" in error_message:
        user_friendly_message = "OpenAI API key is not configured. Please contact support."
    elif "timeout" in error_message.lower():
        user_friendly_message = "Request timed out. Please try again."
    elif "connection" in error_message.lower():
        user_friendly_message = "Connection error. Please check your internet connection."
    
    from fastapi.responses import JSONResponse
    # Return 500 with proper error response
    # This maintains the API contract by returning BrainResponse format
    return JSONResponse(
        status_code=500,
        content={
            "response": f"Error: {user_friendly_message}",
            "model": "gpt-4o-mini",
            "quality_score": 0,
            "quality_checks": {"error": True, "error_type": error_type},
            "error_detail": error_message[:200] if len(error_message) > 200 else error_message  # Truncate long messages
        }
    )

# Register routers


def include_dataset_router(app: FastAPI) -> None:
    """
    Attempt to register the dataset upload router. If python-multipart is missing
    (which FastAPI requires for UploadFile/Form parsing), install instructions
    are returned via a stub endpoint instead of crashing the whole app.
    """
    logger = logging.getLogger("brain")
    try:
        from dataset_upload import router as dataset_router  # local import to catch runtime errors
    except RuntimeError as exc:
        warning = (
            "Dataset upload endpoint is disabled because python-multipart is not installed on the server. "
            "Install python-multipart>=0.0.9 and redeploy to enable image uploads."
        )
        logger.error("Dataset upload router disabled: %s", exc)

        fallback_router = APIRouter(prefix="/api/dataset", tags=["dataset"])

        @fallback_router.post("/upload-image")
        async def dataset_upload_unavailable() -> dict[str, str]:
            raise HTTPException(status_code=503, detail=warning)

        app.include_router(fallback_router)
        return

    app.include_router(dataset_router)


include_dataset_router(app)
app.include_router(image_trust_router, prefix="/api/analyze/image-trust", tags=["image-trust"])
app.include_router(landing_friction_training_router)


# ====================================================
# Local Image Model Helpers (wired to real visual trust model)
# ====================================================

_image_model = None


def get_image_model():
    """
    Lazily load and cache the real visual trust image model used for image_score.

    This reuses the same TensorFlow/Keras model that powers the visual trust engine.
    """
    global _image_model
    logger = logging.getLogger("brain")

    if _image_model is None:
        logger.warning("🧠 Loading visual trust image model for the first time...")
        # Import inside the function to avoid circular imports at module load time
        from visual_trust_engine import _load_model  # type: ignore

        _image_model = _load_model()
        logger.warning("🧠 Visual trust image model loaded and cached.")

    return _image_model


def compute_image_score_from_bytes(data: bytes) -> Optional[float]:
    """
    Use Nima's local image model to compute an image score.

    Returns:
        score in 0–100 range, or None if scoring fails.
    """
    logger = logging.getLogger("brain")
    try:
        # Ensure the underlying visual trust model is loaded (cached globally)
        model = get_image_model()
        _ = model  # prevent linter warnings if unused directly here

        # To stay perfectly aligned with the visual_trust_engine preprocessing and scoring,
        # we write the bytes to a temporary file and call analyze_visual_trust_from_path.
        from visual_trust_engine import analyze_visual_trust_from_path

        project_root = Path(__file__).parent.parent
        tmp_dir = project_root / "dataset" / "tmp_image_score"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        tmp_path = tmp_dir / f"image_score_{uuid4().hex}.jpg"

        with tmp_path.open("wb") as f:
            f.write(data)

        vt = analyze_visual_trust_from_path(str(tmp_path))

        raw_score = float(vt.get("trust_score_numeric"))

        # raw_score is already designed as a 0–100 style numeric trust score
        score = raw_score

        # Clip defensively to [0, 100]
        if score < 0.0:
            score = 0.0
        elif score > 100.0:
            score = 100.0

        logger.warning("🧠 Real image model raw_score=%s, score(0–100)=%s", raw_score, score)
        return float(score)
    except Exception as e:
        logger.error("Error computing image score: %s", e, exc_info=True)
        return None
    finally:
        # Best-effort cleanup of the temporary file
        try:
            if "tmp_path" in locals() and tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            # Non-fatal if cleanup fails
            pass


def _safe_visual_trust_analysis(
    *,
    image_bytes: Optional[bytes],
    image_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run visual trust analysis but never raise exceptions outward.
    Returns a simple dict with percentages and optional error field.
    """
    logger = logging.getLogger("visual_trust")
    base_response: Dict[str, Any] = {
        "overall_label": "not_available",
        "low_percent": 0.0,
        "medium_percent": 0.0,
        "high_percent": 0.0,
        "explanation": "Visual trust analysis not performed.",
        "error": "no_image_provided",
    }

    if not image_bytes:
        return base_response

    tmp_dir = project_root / "dataset" / "tmp_visual_trust"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(image_name or "").suffix or ".png"
    tmp_path = tmp_dir / f"visual_trust_{uuid4().hex}{ext}"

    def _score_for_label(scores: Dict[str, Any], label_keyword: str) -> float:
        for key, value in (scores or {}).items():
            if label_keyword in key.lower():
                try:
                    return float(value) * 100.0
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    try:
        with tmp_path.open("wb") as buffer:
            buffer.write(image_bytes)

        vt = analyze_visual_trust_from_path(str(tmp_path))
        trust_scores = vt.get("trust_scores") or {}

        return {
            "overall_label": vt.get("trust_label") or "unknown",
            "low_percent": _score_for_label(trust_scores, "low"),
            "medium_percent": _score_for_label(trust_scores, "medium"),
            "high_percent": _score_for_label(trust_scores, "high"),
            "explanation": vt.get("visual_comment") or "",
            "error": None,
        }
    except FileNotFoundError as err:
        logger.exception("Visual trust model not found: %s", err)
        response = base_response.copy()
        response["error"] = "visual_trust_model_missing"
        return response
    except Exception as err:
        logger.exception("Visual trust analysis failed: %s", err)
        response = base_response.copy()
        response["error"] = f"visual_trust_analysis_failed: {err}"
        return response
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


# Load system prompt at startup
SYSTEM_PROMPT = load_brain_memory()
QUALITY_ENGINE_ENABLED = True

print("=" * 60)
print("NIMA AI BRAIN API - Starting...")
print("=" * 60)
print(f"System Prompt Length: {len(SYSTEM_PROMPT)} characters")
print(f"Quality Engine: {'Enabled' if QUALITY_ENGINE_ENABLED else 'Disabled'}")
print("=" * 60)


class ChatRequest(BaseModel):
    message: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.7


class BrainRequest(BaseModel):
    role: str = "ai_marketing_strategist"
    locale: str = "tr-TR"
    city: str = "Istanbul"
    industry: str = "restaurant"
    channel: str = "Instagram Ads"
    query: str


class ChatResponse(BaseModel):
    response: str
    model: str


class BrainResponse(BaseModel):
    response: str
    model: str
    quality_score: int = 0
    quality_checks: dict = {}


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Nima AI Brain API",
        "system_prompt_loaded": len(SYSTEM_PROMPT) > 0,
        "system_prompt_length": len(SYSTEM_PROMPT),
        "quality_engine_enabled": QUALITY_ENGINE_ENABLED
    }


@app.post("/api/brain/test")
async def brain_test(
    content: str = Form(""),
    image: Optional[UploadFile] = File(None)
):
    """
    Temporary test endpoint for debugging image upload.
    This endpoint helps verify that images are being received correctly.
    """
    print("📩 REQUEST RECEIVED")
    print("CONTENT:", content)
    
    if image is None:
        print("❌ IMAGE IS NONE")
        return {"debug": "NO_IMAGE", "image_score": 0}
    
    # Reset file pointer to beginning
    await image.seek(0)
    data = await image.read()
    
    print("📸 IMAGE FILENAME:", image.filename)
    print("📏 IMAGE SIZE:", len(data), "bytes")
    print("🔍 FIRST 50 BYTES:", data[:50])
    print("📋 CONTENT TYPE:", image.content_type)
    
    # فقط برای اینکه بدانی تصویر رسید:
    return {
        "debug": "IMAGE_RECEIVED",
        "filename": image.filename,
        "size": len(data),
        "content_type": image.content_type,
        "first_bytes": str(data[:20]) if len(data) >= 20 else str(data)
    }


@app.post("/api/brain")
async def brain_endpoint(
    request: Request,
    content: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
):
    """
    Brain endpoint for marketing strategy queries.
    Accepts both JSON and multipart/form-data:
    
    JSON format:
    - {"query": "text", "role": "...", "city": "...", "industry": "...", "channel": "..."}
    
    Multipart format:
    - content (optional): Text content to analyze
    - image (optional): Image file for visual analysis
    
    At least one of content or image must be provided.
    """
    import logging
    import io
    import json as json_lib
    
    logger = logging.getLogger("brain")
    MIN_TEXT_LENGTH = 0  # عملاً بی‌اثر، فقط می‌گذاریم اگر بعداً خواستی هشدار بدهی
    
    # Image debug variables
    has_image = False
    image_filename = None
    image_size_bytes = 0
    image_score: Optional[float] = None
    
    try:
        # Log request info
        print("\n" + "=" * 60)
        print("=== NIMA BRAIN REQUEST ===")
        content_type = request.headers.get("content-type", "")
        print(f"[/api/brain] Content-Type: {content_type}")
        
        logger.warning("📩 /api/brain called, content=%s", content)
        
        # Determine if request is JSON or multipart
        content_processed = ""
        image_base64: Optional[str] = None
        image_mime: Optional[str] = None
        
        if "application/json" in content_type:
            # Handle JSON request (from frontend)
            try:
                body = await request.json()
                print(f"[/api/brain] JSON request received")
            except json_lib.JSONDecodeError as json_err:
                logger.error(f"JSON parsing error: {json_err}")
                return BrainResponse(
                    response="Error: Invalid JSON format in request. Please check your request data.",
                    model="gpt-4o-mini",
                    quality_score=0,
                    quality_checks={"error": True, "error_type": "json_parse_error"}
                )
            except Exception as json_err:
                logger.error(f"Error parsing JSON request: {json_err}")
                return BrainResponse(
                    response="Error: Failed to parse request. Please check your request format.",
                    model="gpt-4o-mini",
                    quality_score=0,
                    quality_checks={"error": True, "error_type": "request_parse_error"}
                )
            
            # Extract query from JSON body
            query = body.get("query", "")
            # Combine all fields into a comprehensive query if needed
            if query:
                content_processed = query
            else:
                # Build query from individual fields
                role = body.get("role", "")
                city = body.get("city", "")
                industry = body.get("industry", "")
                channel = body.get("channel", "")
                query_text = body.get("query", "")
                
                if query_text:
                    content_processed = query_text
                elif role or city or industry:
                    content_processed = f"{role} analysis for {industry} in {city}"
            
            print(f"[/api/brain] content length: {len(content_processed)}")
            print(f"[/api/brain] has image? False (JSON request)")
            
        else:
            # Handle multipart/form-data request (with image support)
            # Use Form/File parameters if provided, otherwise parse from request
            if content is not None:
                content_processed = content.strip()
                print(f"[/api/brain] Content from Form parameter: {len(content_processed)} chars")
            else:
                form_data = await request.form()
                content_field = form_data.get("content")
                if content_field:
                    content_processed = content_field.strip() if isinstance(content_field, str) else str(content_field)
                else:
                    content_processed = ""
                print(f"[/api/brain] Content from form_data: {len(content_processed)} chars")
            
            # Handle image - prioritize File parameter, then form_data
            if image is not None:
                has_image = True
                await image.seek(0)
                image_data = await image.read()
                image_filename = image.filename
                image_size_bytes = len(image_data)
                image_bytes_raw = image_data
                
                logger.warning("📸 Image received: filename=%s, size=%d bytes", image_filename, image_size_bytes)
                logger.warning("🔍 First 50 bytes: %s", image_data[:50])
                
                # Reset file cursor for further processing
                image.file = io.BytesIO(image_data)
                
                # Compute local image score using Nima's image model (stubbed for now)
                if image_size_bytes > 0:
                    image_score = compute_image_score_from_bytes(image_data)
                    logger.warning("🧠 Local image_score (from model): %s", image_score)
                else:
                    logger.warning("⚠ Empty image data; image_score will be None")
                
                # Convert to base64 for OpenAI API
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                image_mime = image.content_type or "image/png"
                print(f"[/api/brain] Image received: {image_filename}, type: {image_mime}, size: {image_size_bytes} bytes")
            else:
                # Try to get from form_data (if not already read)
                if content is None:
                    form_data = await request.form()
                else:
                    # form_data already read above, get it again
                    form_data = await request.form()
                
                image_field = form_data.get("image")
                if image_field and hasattr(image_field, 'read'):
                    has_image = True
                    image_file: UploadFile = image_field
                    await image_file.seek(0)
                    image_data = await image_file.read()
                    image_filename = image_file.filename
                    image_size_bytes = len(image_data)
                    image_bytes_raw = image_data
                    
                    logger.warning("📸 Image received from form_data: filename=%s, size=%d bytes", image_filename, image_size_bytes)
                    logger.warning("🔍 First 50 bytes: %s", image_data[:50])
                    
                    # Compute local image score using Nima's image model (stubbed for now)
                    if image_size_bytes > 0:
                        image_score = compute_image_score_from_bytes(image_data)
                        logger.warning("🧠 Local image_score (from model): %s", image_score)
                    else:
                        logger.warning("⚠ Empty image data from form_data; image_score will be None")
                    
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
                    image_mime = image_file.content_type or "image/png"
                    print(f"[/api/brain] Image received: {image_filename}, type: {image_mime}, size: {image_size_bytes} bytes")
                else:
                    logger.warning("🚫 No image uploaded in this request")
                    image_base64 = None
                    image_mime = None
        
        # Validate: at least one of content or image must be provided
        if not content_processed and not image_base64:
            raise HTTPException(
                status_code=400,
                detail="No content or image provided. Please upload a screenshot or paste the landing page/ad copy text."
            )

        # Detect whether we are in visual-only mode (image without text)
        text_present = bool(content_processed and content_processed.strip())
        visual_present = bool((image_score is not None) or has_image)
        visual_only_mode = visual_present and not text_present

        logger.warning(
            "🧠 Mode detection: text_present=%s, visual_present=%s, visual_only_mode=%s",
            text_present,
            visual_present,
            visual_only_mode,
        )
        
        print("\n=== SYSTEM PROMPT USED ===")
        print(SYSTEM_PROMPT[:500])
        print("...")
        print(f"(Total length: {len(SYSTEM_PROMPT)} characters)")
        
        print("\n=== QUALITY ENGINE STATUS ===")
        print(f"Quality Engine Active: {QUALITY_ENGINE_ENABLED}")
        print("=" * 60 + "\n")

        # Get response (supports text-only, image-only, or both)
        try:
            print(f"[/api/brain] Calling OpenAI API...")
            if image_score is not None:
                print(f"[/api/brain] Including image_score: {image_score:.1f} in prompt")
            print(f"[/api/brain] visual_only_mode={visual_only_mode}")
            response_text = chat_completion_with_image(
                user_message=content_processed,  # ممکن است خالی باشد
                image_base64=image_base64,
                image_mime=image_mime,
                image_score=image_score,  # Pass image_score to inject into prompt
                visual_only_mode=visual_only_mode,
                model="gpt-4o-mini",
                temperature=0.7
            )
            print(f"[/api/brain] Received response, length: {len(response_text) if response_text else 0}")
            if response_text:
                print(f"[/api/brain] Response preview: {response_text[:200]}...")
        except ValueError as api_error:
            # Catch API key errors and other value errors
            error_msg = str(api_error)
            if "OPENAI_API_KEY" in error_msg:
                error_msg = "OpenAI API key is not configured. Please set OPENAI_API_KEY environment variable."
            print(f"⚠️ Configuration error: {type(api_error).__name__}: {api_error}")
            import traceback
            traceback.print_exc()
            logger.error(f"Configuration error: {api_error}", exc_info=True)
            return BrainResponse(
                response=f"Error: {error_msg}",
                model="gpt-4o-mini",
                quality_score=0,
                quality_checks={"error": True, "error_type": "configuration_error"}
            )
        except Exception as api_error:
            # Catch API errors separately to provide better error messages
            error_type = type(api_error).__name__
            error_msg = str(api_error)
            print(f"⚠️ OpenAI API error: {error_type}: {api_error}")
            import traceback
            traceback.print_exc()
            logger.error(f"OpenAI API error: {error_type}: {api_error}", exc_info=True)
            
            # Provide user-friendly error messages based on error type
            if "Authentication" in error_type or "401" in error_msg:
                user_msg = "OpenAI API authentication failed. Please check your API key."
            elif "RateLimit" in error_type or "429" in error_msg:
                user_msg = "OpenAI API rate limit exceeded. Please try again later."
            elif "Timeout" in error_type or "timeout" in error_msg.lower():
                user_msg = "Request timed out. Please try again."
            else:
                user_msg = "Failed to get response from AI model. Please try again."
            
            return BrainResponse(
                response=f"Error: {user_msg}",
                model="gpt-4o-mini",
                quality_score=0,
                quality_checks={"error": True, "error_type": "api_error", "error_detail": error_type}
            )

        # Quality checks (simplified since we don't have city/industry context anymore)
        quality_checks = {
            "has_examples": any(keyword in response_text.lower() for keyword in ["headline", "hook", "مثال", "example", '"', '«']),
            "has_action_plan": any(keyword in response_text.lower() for keyword in ["0-7", "7-30", "action", "برنامه", "اقدام"]),
            "has_metrics": any(keyword in response_text for keyword in ["%", "درصد", "ctr", "cpc", "cvr"]),
            "has_analysis": any(keyword in response_text.lower() for keyword in ["علت", "cause", "مشکل", "problem", "ریشه"]),
            "has_image_analysis": image_base64 is not None  # Track if image was analyzed
        }
        
        quality_score = sum(quality_checks.values())

        # Build response with image_debug and image_score from local model
        logger.warning("🚀 DEBUG_VERSION: brain-v2-image-score")
        
        result = {
            "response": response_text,
            "model": "gpt-4o-mini",
            "quality_score": quality_score,
            "quality_checks": quality_checks,
            "image_debug": {
                "has_image": has_image,
                "image_filename": image_filename,
                "image_size_bytes": image_size_bytes,
            },
            "image_score": image_score,
            "debug_version": "brain-v2-image-score"
        }
        
        return result
    except HTTPException:
        # Re-raise HTTP exceptions (like 400 Bad Request) as-is
        raise
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e) if str(e) else "Internal error while analyzing content."
        
        print(f"\n❌ ERROR in brain_endpoint: {error_type}: {e}")
        import traceback
        traceback.print_exc()
        logger.error(f"Unhandled error in brain_endpoint: {error_type}: {e}", exc_info=True)
        
        # Return error in BrainResponse format to maintain API contract
        # Clean error message to avoid exposing internal details
        user_friendly_message = "An unexpected error occurred while processing your request."
        
        # Check for specific error patterns and provide user-friendly messages
        if "JSON" in error_message or "json" in error_message.lower() or "No number after minus sign" in error_message or "minus sign" in error_message.lower():
            print(f"⚠️ Detected JSON parsing error pattern: {error_message[:100]}")
            user_friendly_message = "Model response format error. The AI returned an unexpected format. Please try again."
        elif "OPENAI_API_KEY" in error_message:
            user_friendly_message = "OpenAI API key is not configured. Please contact support."
        elif "timeout" in error_message.lower():
            user_friendly_message = "Request timed out. Please try again."
        elif "connection" in error_message.lower() or "network" in error_message.lower():
            user_friendly_message = "Network connection error. Please check your internet connection and try again."
        
        return BrainResponse(
            response=f"Error: {user_friendly_message}",
            model="gpt-4o-mini",
            quality_score=0,
            quality_checks={"error": True, "error_type": error_type}
        )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Chat endpoint using AI brain system prompt.
    
    The system prompt is automatically loaded from:
    - ai_brain/core_brain.md
    - ai_brain/memory_nima.md
    - ai_brain/NIMA_MARKETING_BRAIN.md
    - ai_brain/memory_domain.md
    - ai_brain/memory_actions.md
    - ai_brain/action_engine.md
    - ai_brain/quality_engine.md
    """
    try:
        response_text = chat_completion(
            user_message=request.message,
            model=request.model,
            temperature=request.temperature
        )
        
        return ChatResponse(
            response=response_text,
            model=request.model
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Health check endpoint for deployment monitoring"""
    return {"status": "ok"}


@app.get("/api/system-prompt/info")
def system_prompt_info():
    """Get information about loaded system prompt"""
    # Check which files are loaded
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
    
    file_status = {}
    for name, file_path in files.items():
        file_status[name] = {
            "exists": file_path.exists(),
            "path": str(file_path),
            "size": file_path.stat().st_size if file_path.exists() else 0
        }
    
    return {
        "system_prompt_length": len(SYSTEM_PROMPT),
        "system_prompt_preview": SYSTEM_PROMPT[:500],
        "files": file_status,
        "quality_engine_enabled": QUALITY_ENGINE_ENABLED
    }


@app.post("/api/brain/cognitive-friction", response_model=CognitiveFrictionResult)
async def cognitive_friction_endpoint(
    request: Request,
    raw_text: Optional[str] = Form(None),
    platform: Optional[str] = Form(None),
    goal: Optional[str] = Form(None),
    audience: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    use_trained_model: Optional[str] = Form(None),
):
    """
    Cognitive Friction & Decision Psychology Analysis Endpoint
    
    Analyzes content for cognitive friction, trust, emotional clarity, 
    motivation alignment, and decision probability.
    
    Supports both JSON and multipart/form-data:
    - JSON: Send CognitiveFrictionInput as JSON body
    - Multipart: Send form fields + optional image file
    
    This endpoint uses a specialized AI brain that focuses on:
    - Decision psychology
    - Cognitive friction detection
    - Emotional resistance analysis
    - Trust breakpoint identification
    - Motivation alignment scoring
    - Conversion lift prediction
    
    Returns structured scores and actionable recommendations.
    
    Location: api/main.py (endpoint definition)
    Engine: api/cognitive_friction_engine.py (analysis logic)
    System Prompt: Defined in cognitive_friction_engine.py
    """
    import json as json_lib
    
    try:
        # Handle both JSON and form-data requests
        content_type = request.headers.get("content-type", "")
        image_base64 = None
        image_mime = None
        image_score_value = None
        use_trained_model_flag = False
        image_bytes_raw: Optional[bytes] = None
        image_filename: Optional[str] = None
        
        if "application/json" in content_type:
            # JSON request (may include image as base64 string)
            try:
                body = await request.json()
                
                # Extract image if provided as base64 string in JSON
                
                if body.get("image"):
                    # Image is provided as base64 string
                    image_base64_raw = body.get("image")
                    image_mime = body.get("image_type") or body.get("image_mime") or "image/jpeg"
                    
                    print(f"[/api/brain/cognitive-friction] Image found in JSON body (length: {len(str(image_base64_raw))} chars, type: {image_mime})")
                    
                    # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
                    if isinstance(image_base64_raw, str):
                        if "," in image_base64_raw:
                            # Has data URL prefix
                            image_base64 = image_base64_raw.split(",", 1)[1]
                            # Extract mime type from prefix if available
                            prefix = image_base64_raw.split(",", 1)[0]
                            if "image/" in prefix:
                                extracted_mime = prefix.split("image/")[1].split(";")[0]
                                if extracted_mime:
                                    image_mime = f"image/{extracted_mime}"
                            print(f"[/api/brain/cognitive-friction] Removed data URL prefix, image_base64 length: {len(image_base64)}")
                        else:
                            image_base64 = image_base64_raw
                    else:
                        image_base64 = str(image_base64_raw)
                    
                    # Decode base64 to bytes for image score computation
                    try:
                        image_data = base64.b64decode(image_base64)
                        image_bytes_raw = image_data
                        image_filename = body.get("image_name") or image_filename
                        if len(image_data) > 0:
                            image_score_value = compute_image_score_from_bytes(image_data)
                            print(f"[/api/brain/cognitive-friction] Image score from JSON: {image_score_value}")
                        print(f"[/api/brain/cognitive-friction] Image from JSON: type={image_mime}, size={len(image_data)} bytes")
                    except Exception as img_err:
                        print(f"⚠️ Error processing image from JSON: {img_err}")
                        import traceback
                        traceback.print_exc()
                        # Continue without image score, but keep base64 for API call
                else:
                    print(f"[/api/brain/cognitive-friction] No image found in JSON body")
                
                use_trained_model_flag = bool(body.get("use_trained_model", False))
                # Remove image fields from body before creating input_data
                body_for_input = {
                    k: v
                    for k, v in body.items()
                    if k
                    not in [
                        "image",
                        "image_type",
                        "image_mime",
                        "image_name",
                        "meta",
                        "use_trained_model",
                    ]
                }
                
                # Ensure required fields have defaults
                if "raw_text" not in body_for_input:
                    body_for_input["raw_text"] = ""
                if "platform" not in body_for_input:
                    body_for_input["platform"] = "landing_page"
                if "goal" not in body_for_input:
                    body_for_input["goal"] = ["leads"]
                if "audience" not in body_for_input:
                    body_for_input["audience"] = "cold"
                if "language" not in body_for_input:
                    body_for_input["language"] = "en"
                
                # Ensure goal is a list
                if isinstance(body_for_input.get("goal"), str):
                    try:
                        body_for_input["goal"] = json_lib.loads(body_for_input["goal"])
                    except:
                        body_for_input["goal"] = [body_for_input["goal"]]
                elif not isinstance(body_for_input.get("goal"), list):
                    body_for_input["goal"] = ["leads"]
                
                print(f"[/api/brain/cognitive-friction] Creating input_data with: raw_text='{body_for_input.get('raw_text', '')[:50]}...', platform={body_for_input.get('platform')}, goal={body_for_input.get('goal')}")
                try:
                    input_data = CognitiveFrictionInput(**body_for_input)
                    print(f"[/api/brain/cognitive-friction] ✅ Input data created successfully")
                except Exception as validation_err:
                    print(f"[/api/brain/cognitive-friction] ❌ Validation error: {type(validation_err).__name__}: {validation_err}")
                    import traceback
                    traceback.print_exc()
                    raise HTTPException(status_code=400, detail=f"Invalid input data: {str(validation_err)}")
                
            except json_lib.JSONDecodeError as json_err:
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {json_err}")
            except Exception as parse_err:
                print(f"❌ Error parsing JSON request: {type(parse_err).__name__}: {parse_err}")
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=400, detail=f"Error parsing request: {str(parse_err)}")
        else:
            # Form-data request (with optional image)
            # Parse goal as JSON array if provided as string
            goal_list = ["leads"]  # default
            if goal:
                try:
                    goal_list = json_lib.loads(goal) if isinstance(goal, str) else goal
                    if not isinstance(goal_list, list):
                        goal_list = [goal_list]
                except:
                    goal_list = [goal] if goal else ["leads"]
            
            input_data = CognitiveFrictionInput(
                raw_text=raw_text or "",
                platform=platform or "landing_page",
                goal=goal_list,
                audience=audience or "cold",
                language=language or "en",
                meta={}
            )
            
            # Handle image if provided (multipart/form-data)
            image_base64_form = None
            image_mime_form = None
            image_score_value = None
            if image:
                await image.seek(0)
                image_data = await image.read()
                image_base64_form = base64.b64encode(image_data).decode('utf-8')
                image_mime_form = image.content_type or "image/png"
                
                # Compute image score for visual-only analysis
                if len(image_data) > 0:
                    image_score_value = compute_image_score_from_bytes(image_data)
                    print(f"[/api/brain/cognitive-friction] Image score from form: {image_score_value}")
                
                print(f"[/api/brain/cognitive-friction] Image received from form: {image.filename}, type: {image_mime_form}, size: {len(image_data)} bytes")
            
            # Use form image if available, otherwise use JSON image
            image_base64 = image_base64_form if image_base64_form else image_base64
            image_mime = image_mime_form if image_mime_form else image_mime

            if use_trained_model_form := use_trained_model:
                if isinstance(use_trained_model_form, str):
                    use_trained_model_flag = use_trained_model_form.strip().lower() in {"1", "true", "yes"}
                else:
                    use_trained_model_flag = bool(use_trained_model_form)
        
        # Validate: at least one of text or image must be provided
        has_text = input_data.raw_text and input_data.raw_text.strip()
        has_image = image_base64 is not None and image_mime is not None
        
        print(f"[/api/brain/cognitive-friction] Validation check:")
        print(f"  - has_text: {has_text} (raw_text length: {len(input_data.raw_text) if input_data.raw_text else 0})")
        print(f"  - has_image: {has_image} (image_base64: {image_base64[:50] if image_base64 else None}..., image_mime: {image_mime})")
        
        if not has_text and not has_image:
            error_detail = (
                "Either text (raw_text) or image must be provided for analysis. "
                f"Current status: raw_text={'empty' if not input_data.raw_text or not input_data.raw_text.strip() else 'provided'}, "
                f"image={'not provided' if image_base64 is None else 'provided'}"
            )
            print(f"[/api/brain/cognitive-friction] ❌ Validation failed: {error_detail}")
            raise HTTPException(
                status_code=400,
                detail=error_detail
            )
        
        if use_trained_model_flag and has_image:
            raise HTTPException(
                status_code=400,
                detail="Fine-tuned model currently supports text-only analysis. Remove the image or disable use_trained_model.",
            )

        finetuned_model_id = None
        if use_trained_model_flag:
            try:
                finetuned_model_id = load_psychology_finetune_model_id()
            except FileNotFoundError as err:
                raise HTTPException(status_code=404, detail=str(err)) from err
            except ValueError as err:
                raise HTTPException(status_code=400, detail=str(err)) from err

        # Call analysis with optional image and image_score
        print(f"[/api/brain/cognitive-friction] Calling analyze_cognitive_friction...")
        print(f"  - has_text: {has_text} (length: {len(input_data.raw_text) if input_data.raw_text else 0})")
        print(f"  - has_image: {has_image} (mime: {image_mime})")
        print(f"  - image_score: {image_score_value}")
        print(f"  - use_trained_model: {use_trained_model_flag} (model_id={finetuned_model_id})")
        
        try:
            result = analyze_cognitive_friction(
                input_data,
                image_base64=image_base64,
                image_mime=image_mime,
                image_score=image_score_value,
                model_override=finetuned_model_id,
            )

            visual_trust_payload = _safe_visual_trust_analysis(
                image_bytes=image_bytes_raw,
                image_name=image_filename,
            )
            try:
                result.visual_trust_analysis = VisualTrustAnalysis(**visual_trust_payload)
            except Exception:
                logger.warning("Failed to attach visual trust analysis payload", exc_info=True)

            psychology_payload: Optional[PsychologyAnalysisResult] = None
            if has_text:
                try:
                    advanced_view = analyze_advanced_psychology(
                        input_data.raw_text,
                        platform=input_data.platform,
                        goal=input_data.goal,
                        audience=input_data.audience,
                        language=input_data.language,
                    )
                    psychology_payload = PsychologyAnalysisResult(
                        analysis=None,
                        overall={
                            "summary": "Advanced psychological view generated alongside cognitive friction analysis.",
                            "global_score": None,
                        },
                        human_readable_report="Advanced psychological dashboard data.",
                        advanced_view=advanced_view,
                    )
                except Exception as psych_error:
                    print(
                        f"[/api/brain/cognitive-friction] ⚠️ Advanced psychology analysis failed: {psych_error}"
                    )

            if psychology_payload:
                result.psychology = psychology_payload

            print(f"[/api/brain/cognitive-friction] ✅ Analysis completed successfully")
            return result
        except InvalidAIResponseError as invalid_err:
            print(
                f"\n❌ Invalid AI response structure; returning HTTP 500. raw length={len(invalid_err.raw_output)}"
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "AI returned invalid structure",
                    "raw_output": invalid_err.raw_output,
                },
            )
        except ValueError as ve:
            print(f"\n❌ ValueError in analyze_cognitive_friction: {ve}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=400, detail=f"Invalid input: {ve}")
        except Exception as analysis_error:
            print(f"\n❌ ERROR in analyze_cognitive_friction: {type(analysis_error).__name__}: {analysis_error}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(analysis_error)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ ERROR in cognitive_friction_endpoint: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/brain/image-trust")
async def image_trust_endpoint(input_data: CognitiveFrictionInput):
    """
    Lightweight endpoint that evaluates only the visual trust block.
    Always returns HTTP 200 with an explicit error field instead of raising 500.
    """
    logger = logging.getLogger("brain")
    try:
        image_bytes = None
        if input_data.image:
            try:
                image_bytes = base64.b64decode(input_data.image)
            except Exception as decode_error:
                logger.exception("Invalid base64 payload for image trust: %s", decode_error)
                response = _safe_visual_trust_analysis(image_bytes=None)
                response["error"] = "invalid_image_payload"
                return {"visual_trust_analysis": response}

        visual_payload = _safe_visual_trust_analysis(
            image_bytes=image_bytes,
            image_name=input_data.image_name,
        )
        return {"visual_trust_analysis": visual_payload}
    except Exception as exc:
        logger.exception("Image trust endpoint crashed: %s", exc)
        fallback = _safe_visual_trust_analysis(image_bytes=None)
        fallback["error"] = "visual_trust_endpoint_failed"
        return {"visual_trust_analysis": fallback}


@app.post("/api/brain/rewrite", response_model=RewriteOutput)
async def rewrite_endpoint(input: RewriteInput):
    """
    AI Copy Rewrite Endpoint

    Takes raw marketing text plus context (platform, goal, audience, language)
    and returns 5 rewritten versions + a CTA suggestion.
    """
    return await rewrite_text(input)


@app.post("/api/brain/psychology-analysis", response_model=PsychologyAnalysisResult)
async def psychology_analysis_endpoint(input_data: PsychologyAnalysisInput):
    """
    CORE PSYCHOLOGY ENGINE - 13-Pillar Analysis Endpoint
    
    Analyzes any text using 13 fundamental psychological pillars:
    
    1. Cognitive Friction - Mental effort required to process
    2. Emotional Resonance - Emotional alignment with user's feeling state
    3. Trust & Clarity - Trustworthiness and transparency
    4. Decision Simplicity - Ease of choosing next step
    5. Motivation Profile - Alignment with SDT (Autonomy, Competence, Relatedness)
    6. Behavioral Biases - Cognitive bias detection and usage
    7. Personality Fit - Alignment with personality-driven preferences
    8. Value Perception - Value communication (functional, emotional, symbolic, etc.)
    9. Attention Architecture - Structure for capturing and holding attention
    10. Narrative Clarity - Story flow and structure
    11. Emotional Safety - Psychological safety and comfort
    12. Actionability - Ability to generate immediate action
    13. Identity Alignment - Fit with user's self-identity
    
    Returns:
    - Structured JSON with all 13 pillar analyses (scores, signals, issues, rewrites)
    - Human-readable psychology report
    - Overall summary with global score, top problems, top strengths, recommendations
    
    This endpoint NEVER skips any pillar and always provides:
    - Scores (0-100) for each pillar
    - Explanations and justifications
    - Improved rewrites for each pillar
    - Actionable recommendations
    
    Location: api/main.py (endpoint definition)
    Engine: api/psychology_engine.py (analysis logic)
    System Prompt: Defined in psychology_engine.py
    """
    try:
        result = analyze_psychology(input_data)
        return result
    except Exception as e:
        print(f"\n❌ ERROR in psychology_analysis_endpoint: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/brain/psychology-analysis-with-image")
async def psychology_analysis_with_image(
    text: Optional[str] = Form(None, description="Ad or landing page text to analyze (optional if image is provided)"),
    image: Optional[UploadFile] = File(
        default=None, description="Optional image file for visual trust analysis"
    ),
):
    """
    Extended psychology analysis endpoint that also accepts an optional image.

    Flow:
    1) Run the existing 13-pillar psychology analysis on the provided text.
    2) If an image is provided, run visual trust analysis using the trained model.
    3) Merge visual trust insights into the final JSON response under:

        - visual_trust
        - visual_layer
    
    Supports visual-only mode: if only image is provided (no text), analysis focuses on visual design.
    """
    # Detect visual-only mode: image present but no text
    # Safely handle None text
    text_present = bool(text and text.strip() if text else False)
    visual_present = image is not None
    visual_only_mode = visual_present and not text_present
    
    logger = logging.getLogger("brain")
    logger.warning(
        "🧠 Psychology analysis mode: text_present=%s, visual_present=%s, visual_only_mode=%s",
        text_present,
        visual_present,
        visual_only_mode,
    )
    
    # Validate: at least one must be provided
    if not text_present and not visual_present:
        raise HTTPException(
            status_code=400,
            detail="Either text or image (or both) must be provided for analysis."
        )
    
    # Step 1: Run text-only psychology analysis using existing engine
    input_data = PsychologyAnalysisInput(
        raw_text=text or "",  # Use empty string if None
        platform="visual_ad_or_landing",
        goal=["conversion"],
        audience="general",
        language="auto",
        meta={},
    )

    try:
        base_result = analyze_psychology(input_data, visual_only_mode=visual_only_mode)
    except Exception as e:
        import traceback

        error_msg = str(e)
        print(f"\n❌ ERROR in psychology_analysis_with_image (text analysis): {type(e).__name__}: {error_msg}")
        traceback.print_exc()
        
        # Check if this is a JSON parsing error
        if "JSON" in error_msg or "json" in error_msg.lower() or "No number after minus sign" in error_msg or "minus sign" in error_msg.lower():
            print(f"⚠️ Detected JSON parsing error in psychology analysis: {error_msg[:100]}")
            raise HTTPException(
                status_code=500, 
                detail="Text analysis failed: Model returned an unexpected format. Please try again."
            )
        
        raise HTTPException(status_code=500, detail=f"Text analysis failed: {error_msg}")

    response_payload = base_result.dict()

    # Step 2: If image is provided, run visual trust analysis
    visual_trust = None
    visual_layer = None

    if image is not None:
        project_root = Path(__file__).parent.parent
        tmp_dir = project_root / "dataset" / "tmp_images"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(image.filename or "").suffix or ".jpg"
        tmp_path = tmp_dir / f"psychology_visual_{uuid4().hex}{ext}"

        try:
            # Save uploaded image to a temporary file
            print(f"[VISUAL_ANALYSIS] Reading image file: {image.filename}, content_type: {image.content_type}")
            
            # Reset file pointer to beginning (in case it was read before)
            await image.seek(0)
            content = await image.read()
            
            if not content or len(content) == 0:
                raise ValueError(f"Image file is empty or could not be read: {image.filename}")
            
            print(f"[VISUAL_ANALYSIS] Image read successfully: {len(content)} bytes")
            
            with tmp_path.open("wb") as buffer:
                buffer.write(content)
            
            # Verify file was written
            if not tmp_path.exists() or tmp_path.stat().st_size == 0:
                raise ValueError(f"Failed to save image to temporary path: {tmp_path}")
            
            print(f"[VISUAL_ANALYSIS] Image saved to: {tmp_path} ({tmp_path.stat().st_size} bytes)")
            
            vt = analyze_visual_trust_from_path(str(tmp_path))
            print(f"[VISUAL_ANALYSIS] Visual trust analysis completed: {vt.get('trust_label', 'unknown')}")

            visual_trust = {
                "label": vt.get("trust_label"),
                "score_numeric": vt.get("trust_score_numeric"),
                "scores": vt.get("trust_scores", {}),
            }

            visual_layer = {
                "visual_trust_label": vt.get("trust_label"),
                "visual_trust_score": vt.get("trust_score_numeric"),
                "visual_trust_breakdown": vt.get("trust_scores", {}),
                "visual_trust_scores": vt.get("trust_scores", {}),
                "visual_comment": vt.get("visual_comment", ""),
            }
        except FileNotFoundError as e:
            # Model not trained or file issue: surface as 400 so user can fix setup
            error_msg = str(e)
            print(f"\n❌ FileNotFoundError in visual analysis: {error_msg}")
            if "model not found" in error_msg.lower() or "visual_trust_model" in error_msg.lower():
                # Model not trained - provide helpful message
                visual_trust = {
                    "error": "Visual trust model not trained. The text analysis completed successfully, but visual analysis requires training the model first.",
                    "model_missing": True
                }
                visual_layer = {
                    "visual_trust_label": "N/A",
                    "visual_trust_score": None,
                    "visual_comment": "Visual trust model is not available. Please train the model first using: python training/train_visual_trust_model.py"
                }
            else:
                raise HTTPException(status_code=400, detail=error_msg)
        except ValueError as e:
            # Image reading/saving issues
            error_msg = str(e)
            print(f"\n❌ ValueError in visual analysis: {error_msg}")
            visual_trust = {"error": f"Image processing error: {error_msg}"}
            visual_layer = {
                "visual_trust_label": "N/A",
                "visual_trust_score": None,
                "visual_comment": f"Could not process image: {error_msg}"
            }
        except Exception as e:
            import traceback

            error_msg = str(e)
            print(f"\n❌ ERROR in psychology_analysis_with_image (visual analysis): {type(e).__name__}: {error_msg}")
            traceback.print_exc()
            # We don't want to lose the text analysis result if visual fails
            visual_trust = {
                "error": f"Visual analysis failed: {error_msg}",
                "error_type": type(e).__name__
            }
            visual_layer = {
                "visual_trust_label": "N/A",
                "visual_trust_score": None,
                "visual_comment": f"Visual analysis encountered an error: {error_msg}"
            }
        finally:
            # Clean up temporary file
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                # Non-fatal if cleanup fails
                pass

    # Step 3: Merge visual trust into final response
    if visual_trust is not None:
        response_payload["visual_trust"] = visual_trust
    if visual_layer is not None:
        response_payload["visual_layer"] = visual_layer

    return response_payload


@app.post("/api/brain/analyze-with-image")
async def analyze_with_image(
    text: str = Form(..., description="Ad or landing page text to analyze"),
    image: Optional[UploadFile] = File(
        default=None, description="Optional image file for visual trust analysis"
    ),
):
    """
    Convenience alias for /api/brain/psychology-analysis-with-image.
    Keeps the text-only endpoint intact while adding text+image support.
    """
    return await psychology_analysis_with_image(text=text, image=image)



