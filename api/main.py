"""
FastAPI application with AI brain system prompt - Main entry point

Deployment:
  For Render or similar services, use:
  uvicorn api.main:app --host 0.0.0.0 --port $PORT
  
  Module path: api.main:app
"""
# Load environment variables FIRST, before any other imports that might use os.getenv()
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
else:
    # Fallback to api/.env if it exists
    api_env = Path(__file__).parent / ".env"
    if api_env.exists():
        load_dotenv(api_env, override=True)
    else:
        load_dotenv()  # Load from current directory or system env

import sys
import asyncio

# Safety check: Print PYTHONPATH for deployment diagnostics
print("PYTHONPATH:", sys.path)

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import APIRouter, FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError
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

# REMOVED: sys.path manipulation - not needed when using relative imports
# When running as 'api.main:app', Python already knows 'api' is a package

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

from api.brain_loader import load_brain_memory
from api.chat import chat_completion, chat_completion_with_image
from api.cognitive_friction_engine import (
    analyze_cognitive_friction,
    CognitiveFrictionInput,
    CognitiveFrictionResult,
    InvalidAIResponseError,
    # VisualTrustAnalysis,  # Temporarily disabled
    # VisualTrustResult,  # Temporarily disabled
)
from api.psychology_engine import (
    analyze_psychology,
    analyze_advanced_psychology,
    PsychologyAnalysisInput,
    PsychologyAnalysisResult
)
from api.rewrite_engine import rewrite_text
from api.models.rewrite_models import RewriteInput, RewriteOutput
from api.decision_engine import router as decision_engine_router
from api.visual_trust_engine import analyze_visual_trust_from_path
# TensorFlow removed - no model loading needed
from api.routes.image_trust_local import router as image_trust_local_router
from api.routes.image_trust import router as image_trust_router
from api.routes.training_landing_friction import router as landing_friction_training_router
from api.routes.analyze_url import router as analyze_url_router
from api.routes.analyze_url_human import router as analyze_url_human_router
from api.routes.debug_screenshot import router as debug_screenshot_router
from api.routes.debug import router as debug_router
from api.routes.brain_features import router as brain_features_router
from api.routes.explain import router as explain_router

# Import pricing packages
try:
    from .config.pricing_packages import get_all_packages, PricingTier
except ImportError:
    # Fallback if pricing packages not available
    get_all_packages = None
    PricingTier = None

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

# Startup event: Log environment configuration
@app.on_event("startup")
async def startup_event():
    """Log environment configuration on startup."""
    import logging
    logger = logging.getLogger("brain")
    
    try:
        from api.core.config import get_main_brain_backend_url, is_local_dev
        backend_url = get_main_brain_backend_url()
        env_type = "local-dev" if is_local_dev() else "production"
        logger.info(f"Loaded ENV. MAIN_BRAIN_BACKEND_URL={backend_url} (env={env_type})")
        print(f"✅ Loaded ENV. MAIN_BRAIN_BACKEND_URL={backend_url} (env={env_type})")
    except RuntimeError as e:
        # In local dev, this should never happen (fallback is provided)
        # But if it does, log it and continue - don't crash the server
        from api.core.config import is_local_dev
        if is_local_dev():
            # This shouldn't happen, but if it does, use fallback
            logger.warning(f"Backend URL config issue (should use fallback): {e}")
            print(f"⚠️  Backend URL config issue (using local fallback): {e}")
        else:
            # Production: log error but don't crash - let endpoints handle it
            logger.error(f"Backend URL configuration error: {e}")
            print(f"❌ Backend URL configuration error: {e}")
            print("   Server will start, but endpoints may fail if backend URL is needed.")
    except Exception as e:
        logger.warning(f"Could not load backend URL config: {e}")
        print(f"⚠️  Could not load backend URL config: {e}")
        print("   Server will continue, but some features may not work.")

# Add CORS middleware
# Production: allow frontend domains
# Development: allow localhost for local testing
origins = [
    "https://nimasaraeian.com",
    "https://www.nimasaraeian.com",
    "https://nima-ai-marketing.onrender.com",  # Render deployment
    # Railway deployment: Add your Railway domain here after deploy
    # Example: "https://your-app-name.up.railway.app"
    "http://localhost:3000",  # DEV: Next.js default port
    "http://127.0.0.1:3000",  # DEV: Next.js default port
    "http://localhost:3001",  # DEV: Alternative Next.js port
    "http://127.0.0.1:3001",  # DEV: Alternative Next.js port
    "http://localhost:8000",  # DEV: local development
    "http://127.0.0.1:8000",  # DEV: local development
    "http://localhost:8080",  # DEV: local frontend server
    "http://127.0.0.1:8080",  # DEV: local frontend server
]

# In local development, allow all localhost origins for flexibility
from api.core.config import is_local_dev
if is_local_dev():
    # In local dev, allow all origins for easier development
    # This allows any localhost port to connect
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins in local dev
        allow_credentials=False,  # Must be False when allow_origins is ["*"]
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Production: use specific allowed origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Exception handler for validation errors (422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle FastAPI validation errors (422) with user-friendly messages.
    """
    import logging
    logger = logging.getLogger("brain")
    
    errors = exc.errors()
    error_details = []
    
    for error in errors:
        field = " -> ".join(str(loc) for loc in error.get("loc", []))
        message = error.get("msg", "Validation error")
        error_type = error.get("type", "unknown")
        
        # Translate common error types to user-friendly messages
        user_friendly_msg = message
        if error_type == "missing":
            user_friendly_msg = f"Required field '{field}' is missing"
        elif error_type == "value_error.missing":
            user_friendly_msg = f"Required field '{field}' is missing"
        elif error_type == "type_error":
            user_friendly_msg = f"Invalid data type for field '{field}'. Expected: {message}"
        elif "required" in message.lower():
            user_friendly_msg = f"Required field '{field}' is missing"
        
        error_details.append({
            "field": field,
            "message": user_friendly_msg,
            "type": error_type,
            "original_message": message
        })
        
        logger.warning(f"Validation error: {field} - {message} (type: {error_type})")
        print(f"❌ Validation error: {field} - {user_friendly_msg}")
    
    # Create user-friendly error message
    if len(error_details) == 1:
        error_detail = error_details[0]
        user_message = error_detail['message']
    else:
        fields_list = ", ".join([e['field'] for e in error_details if e['field']])
        user_message = f"Validation errors in {len(error_details)} field(s): {fields_list}. Please check your request data."
    
    print(f"\n❌ VALIDATION ERROR (422): {user_message}")
    print(f"Request path: {request.url.path}")
    print(f"Request method: {request.method}")
    print(f"Error details: {error_details}")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": error_details,
            "message": user_message,
            "error_type": "validation_error",
            "path": request.url.path
        }
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
    
    if "does not contain enough decision-critical" in error_message.lower() or "not contain enough decision-critical" in error_message.lower() or ("image" in error_message.lower() and "decision" in error_message.lower() and "information" in error_message.lower()):
        user_friendly_message = (
            "The image does not contain enough decision-critical information for analysis.\n\n"
            "SOLUTION: Please upload an image that includes:\n"
            "- Pricing information (visible prices, plans, or cost)\n"
            "- Call-to-action buttons or links (Buy, Sign Up, Get Started, etc.)\n"
            "- Guarantees, refund policies, or risk-reduction elements\n"
            "- Headlines or key messaging\n"
            "- Product/service information\n\n"
            "Alternatively, you can:\n"
            "- Paste the text content directly instead of using an image\n"
            "- Provide both image and text together for better analysis\n"
            "- Use a screenshot that captures the full landing page with all decision elements"
        )
    elif "403" in error_message or "forbidden" in error_message.lower() or "blocks automated access" in error_message.lower():
        # Preserve the helpful error message about 403 errors
        user_friendly_message = error_message if "SOLUTION:" in error_message else (
            "This website blocks automated access (403 Forbidden). "
            "Please manually copy the page content (headline, CTA, price, guarantee) "
            "and paste it in the input field instead of the URL."
        )
    elif "OPENAI_API_KEY" in error_message:
        user_friendly_message = "OpenAI API key is not configured. Please contact support."
    elif "timeout" in error_message.lower() or "timed out" in error_message.lower():
        user_friendly_message = error_message if "SOLUTION:" in error_message else "Request timed out. Please try again."
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
        from api.dataset_upload import router as dataset_router  # local import to catch runtime errors
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
app.include_router(image_trust_local_router)
app.include_router(landing_friction_training_router)
app.include_router(analyze_url_router)
app.include_router(analyze_url_human_router)
app.include_router(debug_screenshot_router)
app.include_router(debug_router)
app.include_router(brain_features_router)
app.include_router(explain_router, prefix="", tags=["Explanation"])
app.include_router(
    decision_engine_router,
    prefix="/api/brain",
    tags=["Decision Engine"]
)


# ====================================================
# Local Image Model Helpers (wired to real visual trust model)
# ====================================================

# TensorFlow model loading removed - using OpenCV + local extractor only


# Temporarily disabled - VisualTrustResult import removed
# async def _analyze_visual_trust_with_vision(
#     image_bytes: bytes,
#     mime_type: str = "image/png"
# ) -> VisualTrustResult:
#     """
#     Analyze visual trust using OpenAI Vision API.
#     
#     Args:
#         image_bytes: Raw image bytes
#         mime_type: MIME type of the image
#     
#     Returns:
#         VisualTrustResult with elements and narrative
#     """
#     logger = logging.getLogger("visual_trust")
#     try:
        # Encode image to base64
#        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
#        data_url = f"data:{mime_type};base64,{image_b64}"
#        
        # Get OpenAI client
#        from cognitive_friction_engine import get_client, VISUAL_TRUST_SYSTEM_PROMPT
#        client = get_client()
#        
        # Call Vision API
#        logger.info("Calling OpenAI Vision API for visual trust analysis...")
#        logger.info(f"Image size: {len(image_bytes)} bytes, MIME type: {mime_type}")
#        
#        user_message_content = [
#            {"type": "text", "text": "Analyze this landing page screenshot."},
#            {
#                "type": "image_url",
#                "image_url": {
#                    "url": data_url
#                },
#            },
#        ]
#        
#        response = client.chat.completions.create(
#            model="gpt-4o-mini",
#            messages=[
#                {"role": "system", "content": VISUAL_TRUST_SYSTEM_PROMPT},
#                {
#                    "role": "user",
#                    "content": user_message_content,
#                },
#            ],
#            temperature=0.2,
#            max_tokens=3000,  # Increased to ensure we get enough elements and narrative
#        )
#        
        # Parse response
#        raw_content = response.choices[0].message.content
#        logger.info(f"[DEBUG] Vision API raw response (first 500 chars): {raw_content[:500]}")
#        logger.info(f"[DEBUG] Vision API raw response length: {len(raw_content)} chars")
#        
        # Extract JSON (handle markdown code blocks if present)
#        raw_json = raw_content
#        if "```json" in raw_json:
#            logger.debug("Found ```json markdown block, extracting JSON...")
#            raw_json = raw_json.split("```json")[1].split("```")[0].strip()
#        elif "```" in raw_json:
#            logger.debug("Found ``` markdown block, extracting JSON...")
#            raw_json = raw_json.split("```")[1].split("```")[0].strip()
#        
#        logger.info(f"[DEBUG] Extracted JSON (first 500 chars): {raw_json[:500]}")
#        
        # Parse JSON with error handling
#        try:
#            data = json.loads(raw_json)
#            logger.info(f"[DEBUG] Successfully parsed JSON. Keys: {list(data.keys())}")
#        except json.JSONDecodeError as json_err:
#            logger.error(f"[DEBUG] JSON parsing failed! Error: {json_err}")
#            logger.error(f"[DEBUG] Raw JSON that failed to parse (first 1000 chars): {raw_json[:1000]}")
#            raise json_err
#        
        # Convert to VisualTrustResult + VisualElement list
#        from cognitive_friction_engine import VisualElement
#        elements = []
#        raw_elements = data.get("elements", [])
#        logger.info(f"[DEBUG] Found {len(raw_elements)} raw elements in response")
#        
#        for idx, e in enumerate(raw_elements):
#            try:
#                element = VisualElement(
#                    id=e.get("id", f"element_{len(elements)}"),
#                    role=e.get("role", "other"),
#                    approx_position=e.get("approx_position", "middle-center"),
#                    text=e.get("text"),
#                    visual_cues=e.get("visual_cues") or [],
#                    analysis=e.get("analysis") or {},
#                )
#                elements.append(element)
#                logger.debug(f"[DEBUG] Successfully parsed element {idx+1}: {element.id} ({element.role})")
#            except Exception as elem_err:
#                logger.warning(f"[DEBUG] Failed to parse element {idx+1}: {e}, error: {elem_err}")
#                continue
#        
#        overall = data.get("overall_visual_trust") or {}
#        narrative = data.get("narrative") or []
#        
#        logger.info(f"[DEBUG] Parsed {len(elements)} elements, {len(narrative)} narrative items")
#        logger.info(f"[DEBUG] Overall trust data: {overall}")
#        
        # Validate minimum requirements
#        if len(elements) < 3:
#            logger.warning(
#                f"[DEBUG] Insufficient elements: got {len(elements)}, expected at least 3. "
#                f"Raw elements: {raw_elements}"
#            )
#        
#        if len(narrative) < 2:
#            logger.warning(
#                f"[DEBUG] Insufficient narrative: got {len(narrative)}, expected at least 2. "
#                f"Raw narrative: {narrative}"
#            )
#        
        # Normalize label
#        from typing import Literal
#        label_raw = overall.get("label", "").strip()
#        label: Optional[Literal["Low", "Medium", "High"]] = None
#        if label_raw:
#            label_lower = label_raw.lower()
#            if "low" in label_lower:
#                label = "Low"
#            elif "medium" in label_lower:
#                label = "Medium"
#            elif "high" in label_lower:
#                label = "High"
#        
#        overall_score = overall.get("score")
#        if overall_score is not None:
#            overall_score = float(overall_score)
#            overall_score = max(0.0, min(100.0, overall_score))
#        
        # Determine status based on data quality
#        status = "ok"
#        notes = None
#        
#        if len(elements) < 3 or len(narrative) < 2:
#            status = "fallback"
#            notes = (
#                f"Visual structure analysis returned insufficient data "
#                f"(elements: {len(elements)}, narrative: {len(narrative)}). "
#                f"This is a partial result."
#            )
#            logger.warning(f"[DEBUG] Setting status to 'fallback' due to insufficient data")
#        
#        result = VisualTrustResult(
#            status=status,
#            label=label,
#            overall_score=overall_score,
#            distribution=None,
#            notes=notes,
#            elements=elements,
#            narrative=narrative,
#        )
#        
#        logger.info(
#            f"Vision API analysis completed: status={status}, label={label}, score={overall_score}, "
#            f"elements={len(elements)}, narrative_items={len(narrative)}"
#        )
#        
#        return result
#        
#    except json.JSONDecodeError as e:
#        logger.error(f"[DEBUG] JSON parsing failed with error: {e}")
#        logger.error(f"[DEBUG] Error at position {e.pos if hasattr(e, 'pos') else 'unknown'}")
#        logger.error(f"[DEBUG] Raw content that failed (first 1000 chars): {raw_content[:1000] if 'raw_content' in locals() else 'N/A'}")
#        return VisualTrustResult(
#            status="fallback",
#            label="Medium",
#            overall_score=60.0,
#            distribution={"low": 0.3, "medium": 0.5, "high": 0.2},
#            notes="Visual structure analysis could not be fully parsed. This is a heuristic fallback.",
#            elements=[],
#            narrative=[
#                "Visual structure analysis could not be fully parsed. This is a heuristic fallback.",
#                "The AI vision model response was not in the expected JSON format."
#            ],
#        )
#    except Exception as e:
#        logger.exception(f"[DEBUG] Vision API visual trust analysis failed: {e}")
#        logger.error(f"[DEBUG] Exception type: {type(e).__name__}")
#        logger.error(f"[DEBUG] Exception details: {str(e)}")
#        import traceback
#        logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
#        return VisualTrustResult(
#            status="fallback",
#            label="Medium",
#            overall_score=60.0,
#            distribution={"low": 0.3, "medium": 0.5, "high": 0.2},
#            notes=f"Visual structure analysis could not be fully parsed. Error: {str(e)}. This is a heuristic fallback.",
#            elements=[],
#            narrative=[
#                "Visual structure analysis could not be fully parsed. This is a heuristic fallback.",
#                f"The AI vision model encountered an error: {type(e).__name__}"
#            ],
#        )
#

# Temporarily disabled - VisualTrustResult import removed
# def _build_visual_trust_result(
#     *,
#     trust_label: Optional[str] = None,
#     trust_scores: Optional[Dict[str, float]] = None,
#     trust_score_numeric: Optional[float] = None,
#     status: str = "unavailable",
#     notes: Optional[str] = None,
#     error: Optional[str] = None,
# ) -> VisualTrustResult:
#     """
#     Build a unified VisualTrustResult from various visual trust data sources.
    
#    Args:
#        trust_label: Trust label from model ("low", "medium", "high")
#        trust_scores: Distribution scores {"low": float, "medium": float, "high": float}
#        trust_score_numeric: Overall numeric score (0-100)
#        status: Status of the analysis ("ok", "fallback", "unavailable")
#        notes: Optional notes explaining the result
#        error: Optional error message
    
#    Returns:
#        VisualTrustResult object
#    """
    # Normalize label to proper case
#    label: Optional[str] = None
#    if trust_label:
#        label_lower = trust_label.lower()
#        if label_lower == "low":
#            label = "Low"
#        elif label_lower == "medium":
#            label = "Medium"
#        elif label_lower == "high":
#            label = "High"
    
    # Use provided score or calculate from distribution
#    overall_score: Optional[float] = trust_score_numeric
#    if overall_score is None and trust_scores:
        # Weighted average: low=0-33, medium=34-66, high=67-100
#        low_weight = trust_scores.get("low", 0.0) * 16.5
#        medium_weight = trust_scores.get("medium", 0.0) * 50.0
#        high_weight = trust_scores.get("high", 0.0) * 83.5
#        overall_score = low_weight + medium_weight + high_weight
    
    # Normalize distribution to percentages (0-100)
#    distribution: Optional[Dict[str, float]] = None
#    if trust_scores:
#        distribution = {
#            "low": trust_scores.get("low", 0.0) * 100.0,
#            "medium": trust_scores.get("medium", 0.0) * 100.0,
#            "high": trust_scores.get("high", 0.0) * 100.0
#        }
    
    # Build notes from error if needed
#    final_notes = notes
#    if error and not final_notes:
#        if "model_missing" in error or "model not found" in error.lower():
#            final_notes = "Visual trust model not loaded on server. Using fallback estimation."
#        elif "fallback" in error.lower():
#            final_notes = "Visual trust model not available. Using fallback estimation."
#        else:
#            final_notes = f"Visual trust analysis encountered an error: {error}"
    
#    return VisualTrustResult(
#        status=status,
#        label=label,
#        overall_score=overall_score,
#        distribution=distribution,
#        notes=final_notes
#    )


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
        response["error"] = "visual_trust_analysis_unavailable"
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
print("VisualTrust: Using OpenCV + local extractor (no TensorFlow)")
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
                
                # Image score computation removed (TensorFlow dependency removed)
                # Using OpenCV + local extractor for visual trust analysis instead
                if image_size_bytes > 0:
                    image_score = None  # Not computed (TensorFlow removed)
                    logger.info("🧠 Image score computation disabled (TensorFlow removed)")
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
                    
                    # Image score computation removed (TensorFlow dependency removed)
                    if image_size_bytes > 0:
                        image_score = None  # Not computed (TensorFlow removed)
                        logger.info("🧠 Image score computation disabled (TensorFlow removed)")
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
        if "does not contain enough decision-critical" in error_message.lower() or "not contain enough decision-critical" in error_message.lower() or ("image" in error_message.lower() and "decision" in error_message.lower() and "information" in error_message.lower()):
            user_friendly_message = (
                "The image does not contain enough decision-critical information for analysis.\n\n"
                "SOLUTION: Please upload an image that includes:\n"
                "- Pricing information (visible prices, plans, or cost)\n"
                "- Call-to-action buttons or links (Buy, Sign Up, Get Started, etc.)\n"
                "- Guarantees, refund policies, or risk-reduction elements\n"
                "- Headlines or key messaging\n"
                "- Product/service information\n\n"
                "Alternatively, you can:\n"
                "- Paste the text content directly instead of using an image\n"
                "- Provide both image and text together for better analysis\n"
                "- Use a screenshot that captures the full landing page with all decision elements"
            )
        elif "403" in error_message or "forbidden" in error_message.lower() or "blocks automated access" in error_message.lower():
            # Preserve the helpful error message about 403 errors
            user_friendly_message = error_message if "SOLUTION:" in error_message else (
                "This website blocks automated access (403 Forbidden). "
                "Please manually copy the page content (headline, CTA, price, guarantee) "
                "and paste it in the input field instead of the URL."
            )
        elif "JSON" in error_message or "json" in error_message.lower() or "No number after minus sign" in error_message or "minus sign" in error_message.lower():
            print(f"⚠️ Detected JSON parsing error pattern: {error_message[:100]}")
            user_friendly_message = "Model response format error. The AI returned an unexpected format. Please try again."
        elif "OPENAI_API_KEY" in error_message:
            user_friendly_message = "OpenAI API key is not configured. Please contact support."
        elif "timeout" in error_message.lower() or "timed out" in error_message.lower():
            user_friendly_message = error_message if "SOLUTION:" in error_message else "Request timed out. Please try again."
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


@app.get("/debug/env")
def debug_env():
    """
    Debug endpoint to show environment configuration (local dev only).
    
    Returns 404 in production for security.
    """
    from api.core.config import is_local_dev, get_debug_env_info
    
    if not is_local_dev():
        raise HTTPException(status_code=404, detail="Not found")
    
    return get_debug_env_info()


@app.get("/api/packages")
async def get_packages():
    """
    Get all pricing packages for Decision Brain services.
    
    Returns the 3-tier package structure:
    - Decision Diagnosis (Entry)
    - Decision Deep Dive (High-Value Project)
    - Decision Strategy Partnership (Advisory)
    """
    logger = logging.getLogger("brain")
    if get_all_packages is None:
        raise HTTPException(
            status_code=503,
            detail="Pricing packages configuration not available"
        )
    
    try:
        packages = get_all_packages()
        # Convert to dict format for JSON response
        packages_data = []
        for package in packages:
            packages_data.append({
                "tier": package.tier.value,
                "name": package.name,
                "positioning_line": package.positioning_line,
                "features": [
                    {
                        "title": feature.title,
                        "description": feature.description
                    }
                    for feature in package.features
                ],
                "pricing_note": package.pricing_note,
                "cta_text": package.cta_text,
                "cta_route": package.cta_route
            })
        
        return {
            "packages": packages_data,
            "total_tiers": len(packages_data)
        }
    except Exception as e:
        logger.error(f"Error retrieving packages: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve packages: {str(e)}"
        )


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
    url: Optional[str] = Form(None),
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
    logger = logging.getLogger("brain")
    
    # Wrap entire endpoint in timeout (120 seconds total)
    try:
        return await asyncio.wait_for(
            _cognitive_friction_endpoint_internal(
                request, raw_text, platform, goal, audience, language, url, image, use_trained_model
            ),
            timeout=120.0
        )
    except asyncio.TimeoutError:
        logger.error("Cognitive friction endpoint timed out after 120 seconds")
        raise HTTPException(
            status_code=504,
            detail=(
                "Request timed out. The analysis took too long to complete.\n\n"
                "This can happen if:\n"
                "- The website is slow to scrape\n"
                "- The AI model is taking longer than expected\n\n"
                "SOLUTION: Please try again, or paste the page content directly instead of using a URL."
            )
        )


async def _cognitive_friction_endpoint_internal(
    request: Request,
    raw_text: Optional[str],
    platform: Optional[str],
    goal: Optional[str],
    audience: Optional[str],
    language: Optional[str],
    url: Optional[str],
    image: Optional[UploadFile],
    use_trained_model: Optional[str],
):
    """Internal implementation of cognitive friction endpoint."""
    import json as json_lib
    logger = logging.getLogger("brain")
    
    try:
        # Parse request body
        content_type = request.headers.get("content-type", "")
        
        # Initialize variables (all inside try block)
        image_base64 = None
        image_mime = None
        image_score_value = None
        use_trained_model_flag = False
        input_data: Optional[CognitiveFrictionInput] = None
        
        if "application/json" in content_type:
            # JSON request
            body = await request.json()
            
            # Extract and process image if provided
            if body.get("image"):
                image_base64_raw = body.get("image")
                image_mime = body.get("image_type") or body.get("image_mime") or "image/jpeg"
                
                # Remove data URL prefix if present
                if isinstance(image_base64_raw, str):
                    if "," in image_base64_raw:
                        image_base64 = image_base64_raw.split(",", 1)[1]
                        prefix = image_base64_raw.split(",", 1)[0]
                        if "image/" in prefix:
                            extracted_mime = prefix.split("image/")[1].split(";")[0]
                            if extracted_mime:
                                image_mime = f"image/{extracted_mime}"
                    else:
                        image_base64 = image_base64_raw
                
                # Compute image score
                try:
                    image_data = base64.b64decode(image_base64)
                    if len(image_data) > 0:
                        image_score_value = None  # Not computed (TensorFlow removed)
                except Exception:
                    pass  # Continue without image score
            
            use_trained_model_flag = bool(body.get("use_trained_model", False))
            
            # Extract raw text (support multiple field names)
            raw_text_value = (body.get("pageCopy") or body.get("page_copy") or body.get("raw_text") or "").strip()
            
            # Extract URL (support multiple field names)
            url_value = body.get("url") or body.get("target_url") or None
            if url_value:
                url_value = url_value.strip() if isinstance(url_value, str) else None
            print(f"[/api/brain/cognitive-friction] 🔍 Extracted URL from body: {url_value}")
            
            # Extract meta fields
            meta_dict = body.get("meta", {}) or {}
            if not isinstance(meta_dict, dict):
                meta_dict = {}
            
            # Normalize price_level
            price_level_raw = body.get("priceLevel") or body.get("price_level")
            price_level_normalized = None
            if price_level_raw:
                price_level_map = {
                    "Low": "Low (Impulse)",
                    "Medium": "Medium (Considered)",
                    "High": "High (High-risk)",
                    "low": "Low (Impulse)",
                    "medium": "Medium (Considered)",
                    "high": "High (High-risk)",
                }
                price_level_normalized = price_level_map.get(price_level_raw) or price_level_map.get(price_level_raw.strip().capitalize())
            
            # Normalize decision_depth
            decision_depth_raw = body.get("decisionDepth") or body.get("decision_depth")
            decision_depth_normalized = None
            if decision_depth_raw:
                decision_depth_map = {
                    "Impulse": "Impulse",
                    "Considered": "Considered",
                    "High-commitment": "High-Commitment",
                    "High-Commitment": "High-Commitment",
                    "high-commitment": "High-Commitment",
                    "impulse": "Impulse",
                    "considered": "Considered",
                }
                decision_depth_normalized = decision_depth_map.get(decision_depth_raw)
                if not decision_depth_normalized:
                    decision_depth_normalized = decision_depth_map.get(decision_depth_raw.lower())
                if not decision_depth_normalized:
                    depth_lower = decision_depth_raw.lower().strip()
                    if "high" in depth_lower and "commitment" in depth_lower:
                        decision_depth_normalized = "High-Commitment"
                    elif depth_lower == "impulse":
                        decision_depth_normalized = "Impulse"
                    elif depth_lower == "considered":
                        decision_depth_normalized = "Considered"
            
            # Normalize user_intent_stage
            user_intent_raw = body.get("userIntent") or body.get("user_intent") or body.get("user_intent_stage")
            user_intent_normalized = None
            if user_intent_raw:
                user_intent_map = {
                    "Learn": "Learn",
                    "Compare": "Compare",
                    "Validate": "Validate",
                    "Buy": "Buy",
                }
                user_intent_normalized = user_intent_map.get(user_intent_raw, user_intent_raw)
            
            # Normalize goal
            goal_value = body.get("goal", ["leads"])
            if isinstance(goal_value, str):
                try:
                    goal_value = json_lib.loads(goal_value)
                except:
                    goal_value = [goal_value]
            if not isinstance(goal_value, list):
                goal_value = [goal_value] if goal_value else ["leads"]
            
            # Build meta dict
            meta_final = {}
            for key, value in meta_dict.items():
                if value is not None:
                    meta_final[key] = value
            
            # Add URL and page_type to meta if provided at top level (for backward compatibility)
            if "url" in body and body.get("url"):
                meta_final["url"] = body.get("url")
            if "pageType" in body:
                meta_final["page_type"] = body.get("pageType")
            elif "page_type" in body:
                meta_final["page_type"] = body.get("page_type")
            
            # Build body_for_input - ONLY ONCE, inside try block
            body_for_input = {
                "raw_text": raw_text_value,
                "platform": body.get("platform", "landing_page"),
                "goal": goal_value,
                "audience": body.get("audience", "cold"),
                "language": body.get("language", "en"),
                "meta": meta_final,
            }
            
            # Add URL if provided (prefer top-level url_value, fallback to meta url)
            if url_value:
                body_for_input["url"] = url_value
                print(f"[/api/brain/cognitive-friction] ✅ Added URL to body_for_input: {url_value}")
            elif meta_final.get("url"):
                body_for_input["url"] = meta_final.get("url")
                print(f"[/api/brain/cognitive-friction] ✅ Added URL from meta to body_for_input: {meta_final.get('url')}")
            else:
                print(f"[/api/brain/cognitive-friction] ⚠️ No URL found in body or meta")
            
            # Add optional fields if normalized
            if price_level_normalized:
                body_for_input["price_level"] = price_level_normalized
            if decision_depth_normalized:
                body_for_input["decision_depth"] = decision_depth_normalized
            if user_intent_normalized:
                body_for_input["user_intent_stage"] = user_intent_normalized
            if "businessType" in body:
                body_for_input["business_type"] = body.get("businessType")
            elif "business_type" in body:
                body_for_input["business_type"] = body.get("business_type")
            
            # Validate using Pydantic
            try:
                print(f"[/api/brain/cognitive-friction] 📦 Creating CognitiveFrictionInput with: url={body_for_input.get('url')}, raw_text length={len(body_for_input.get('raw_text', ''))}")
                input_data = CognitiveFrictionInput(**body_for_input)
                print(f"[/api/brain/cognitive-friction] ✅ Input data created. input_data.url={getattr(input_data, 'url', 'NOT SET')}")
            except ValidationError as ve:
                print(f"[/api/brain/cognitive-friction] ❌ Validation error: {ve}")
                raise HTTPException(status_code=400, detail=f"Invalid input data: {ve}")
            
        else:
            # Form-data request
            goal_list = ["leads"]
            if goal:
                try:
                    goal_list = json_lib.loads(goal) if isinstance(goal, str) else goal
                    if not isinstance(goal_list, list):
                        goal_list = [goal_list]
                except:
                    goal_list = [goal] if goal else ["leads"]
            
            # Extract URL from form data if provided
            url_from_form = None
            if url:
                url_from_form = url.strip() if isinstance(url, str) else None
            
            input_data_dict = {
                "raw_text": raw_text or "",
                "platform": platform or "landing_page",
                "goal": goal_list,
                "audience": audience or "cold",
                "language": language or "en",
                "meta": {}
            }
            
            # Add URL if provided
            if url_from_form:
                input_data_dict["url"] = url_from_form
            
            input_data = CognitiveFrictionInput(**input_data_dict)
            
            # Handle image if provided (multipart/form-data)
            if image:
                await image.seek(0)
                image_data = await image.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                image_mime = image.content_type or "image/png"
                
                if len(image_data) > 0:
                    image_score_value = None  # Not computed (TensorFlow removed)
            
            if use_trained_model:
                if isinstance(use_trained_model, str):
                    use_trained_model_flag = use_trained_model.strip().lower() in {"1", "true", "yes"}
                else:
                    use_trained_model_flag = bool(use_trained_model)
        
        # Validate: at least one of text, image, or URL must be provided (BEFORE scraping)
        has_text = input_data.raw_text and input_data.raw_text.strip()
        has_image = image_base64 is not None and image_mime is not None
        # Check URL - try both input_data.url and meta.url
        has_url = False
        url_for_validation = None
        if hasattr(input_data, 'url') and input_data.url:
            url_for_validation = input_data.url.strip() if isinstance(input_data.url, str) else None
            has_url = bool(url_for_validation)
        elif input_data.meta and input_data.meta.get("url"):
            url_for_validation = input_data.meta.get("url")
            has_url = bool(url_for_validation)
        
        print(f"[/api/brain/cognitive-friction] 🔍 Validation check (BEFORE scraping): has_text={has_text}, has_image={has_image}, has_url={has_url} (url={url_for_validation})")
        
        # Only raise error if we have NO input at all
        if not has_text and not has_image and not has_url:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Please provide either page copy text, a screenshot, or a URL for analysis. "
                    f"Current status: raw_text={'empty' if not input_data.raw_text or not input_data.raw_text.strip() else 'provided'}, "
                    f"image={'not provided' if image_base64 is None else 'provided'}, "
                    f"url={'not provided' if not has_url else 'provided'}"
                )
            )
        
        # If raw_text is empty but URL is provided (either in url field or meta), try to scrape the page
        if not input_data.raw_text or not input_data.raw_text.strip():
            # Try to get URL from input_data.url first, then from meta
            url_to_scrape = None
            if hasattr(input_data, 'url') and input_data.url:
                url_to_scrape = input_data.url.strip() if isinstance(input_data.url, str) else None
            elif input_data.meta and input_data.meta.get("url"):
                url_to_scrape = input_data.meta.get("url")
            
            if url_to_scrape:
                print(f"[/api/brain/cognitive-friction] 🔍 Attempting to scrape URL: {url_to_scrape}")
                try:
                    from api.utils.decision_snapshot_extractor import extract_decision_snapshot, format_snapshot_text
                    # Add timeout to scraping (45 seconds max)
                    snapshot = await asyncio.wait_for(
                        extract_decision_snapshot(url_to_scrape),
                        timeout=45.0
                    )
                    scraped_text = format_snapshot_text(snapshot)
                    input_data.raw_text = scraped_text
                    print(f"[/api/brain/cognitive-friction] ✅ Successfully scraped {len(scraped_text)} characters from URL")
                except asyncio.TimeoutError:
                    error_msg = "URL scraping timed out after 45 seconds. The website may be slow or blocking automated access."
                    print(f"[/api/brain/cognitive-friction] ❌ Scraping timeout: {error_msg}")
                    raise HTTPException(
                        status_code=408,
                        detail=(
                            f"{error_msg}\n\n"
                            "SOLUTION: Please manually copy and paste the page content:\n"
                            "- Hero headline\n"
                            "- CTA button text\n"
                            "- Price (if visible)\n"
                            "- Guarantee/refund information\n\n"
                            "Then paste this content in the 'Page Copy' field instead of using the URL."
                        )
                    )
                except Exception as scrape_err:
                    error_msg = str(scrape_err)
                    print(f"[/api/brain/cognitive-friction] ❌ Scraping failed: {error_msg}")
                    raise HTTPException(
                        status_code=400,
                        detail=error_msg if "SOLUTION:" in error_msg else (
                            f"Failed to scrape content from URL: {error_msg}\n\n"
                            "SOLUTION: Please manually copy and paste the page content:\n"
                            "- Hero headline\n"
                            "- CTA button text\n"
                            "- Price (if visible)\n"
                            "- Guarantee/refund information\n\n"
                            "Then paste this content in the 'Page Copy' field instead of using the URL."
                        )
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
        
        # Run analysis with timeout (90 seconds max for the entire analysis)
        # analyze_cognitive_friction is a sync function, so we run it in a thread
        try:
            if hasattr(asyncio, 'to_thread'):
                # Python 3.9+
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        analyze_cognitive_friction,
                        input_data,
                        image_base64=image_base64,
                        image_mime=image_mime,
                        image_score=image_score_value,
                        model_override=finetuned_model_id,
                    ),
                    timeout=90.0
                )
            else:
                # Python < 3.9
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: analyze_cognitive_friction(
                            input_data,
                            image_base64=image_base64,
                            image_mime=image_mime,
                            image_score=image_score_value,
                            model_override=finetuned_model_id,
                        )
                    ),
                    timeout=90.0
                )
        except asyncio.TimeoutError:
            logger.error("Cognitive friction analysis timed out after 90 seconds")
            raise HTTPException(
                status_code=504,
                detail=(
                    "Analysis timed out. The request took too long to process.\n\n"
                    "This can happen if:\n"
                    "- The website is slow to scrape\n"
                    "- The AI model is taking longer than expected\n\n"
                    "SOLUTION: Please try again, or paste the page content directly instead of using a URL."
                )
            )
        
        # Add advanced psychology analysis if text is available
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
                result.psychology = psychology_payload
            except Exception:
                pass  # Continue without advanced psychology
        
        return result
        
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=f"Invalid input: {ve}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in cognitive_friction_endpoint: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


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
    # visual_trust_result: Optional[VisualTrustResult] = None  # Temporarily disabled
    visual_trust_result = None

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
            
            # Build unified VisualTrustResult - Temporarily disabled
            # visual_trust_result = _build_visual_trust_result(
            #     trust_label=vt.get("trust_label"),
            #     trust_scores=vt.get("trust_scores", {}),
            #     trust_score_numeric=vt.get("trust_score_numeric"),
            #     status="ok",
            #     notes=vt.get("visual_comment")
            # )
            visual_trust_result = None
        except FileNotFoundError as e:
            # Model not trained or file issue: surface as 400 so user can fix setup
            error_msg = str(e)
            print(f"\n❌ FileNotFoundError in visual analysis: {error_msg}")
            if "model not found" in error_msg.lower() or "visual_trust_model" in error_msg.lower() or "visual_trust_analysis" in error_msg.lower():
                # Model not trained - provide helpful message
                visual_trust = {
                    "error": "Visual trust model not trained. The text analysis completed successfully, but visual analysis requires training the model first.",
                    "model_missing": True
                }
                visual_layer = {
                    "visual_trust_label": "N/A",
                    "visual_trust_score": None,
                    "visual_comment": "Visual trust analysis uses OpenCV + local extractor (no TensorFlow model required)"
                }
                # Build fallback VisualTrustResult - Temporarily disabled
                # visual_trust_result = _build_visual_trust_result(
                #     status="fallback",
                #     notes="Visual trust model not loaded on server. Using fallback estimation."
                # )
                visual_trust_result = None
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
            # visual_trust_result = _build_visual_trust_result(  # Temporarily disabled
            #     status="unavailable",
            #     error=error_msg,
            #     notes=f"Could not process image: {error_msg}"
            # )
            visual_trust_result = None
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
            # visual_trust_result = _build_visual_trust_result(  # Temporarily disabled
            #     status="unavailable",
            #     error=error_msg,
            #     notes=f"Visual analysis encountered an error: {error_msg}"
            # )
            visual_trust_result = None
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
    # Always set unified visual_trust_result (even if unavailable) - Temporarily disabled
    # if visual_trust_result is not None:
    #     response_payload["visual_trust_result"] = visual_trust_result.dict()
    # else:
    #     # No image provided - set unavailable status
    #     response_payload["visual_trust_result"] = _build_visual_trust_result(
    #         status="unavailable",
    #         notes="Visual trust analysis was not performed for this landing page."
    #     ).dict()
    # VisualTrustResult temporarily disabled

    return response_payload


@app.post("/api/brain/analyze-with-image")
async def analyze_with_image(
    text: Optional[str] = Form(None, description="Ad or landing page text to analyze (optional if image is provided)"),
    image: Optional[UploadFile] = File(
        default=None, description="Optional image file for visual trust analysis"
    ),
):
    """
    Convenience alias for /api/brain/psychology-analysis-with-image.
    Keeps the text-only endpoint intact while adding text+image support.
    """
    return await psychology_analysis_with_image(text=text, image=image)


