"""
FastAPI application with AI brain system prompt - Main entry point

Deployment:
  For Render or similar services, use:
  uvicorn api.main:app --host 0.0.0.0 --port $PORT
  
  Module path: api.main:app
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import sys
import base64
import json
from pathlib import Path
from typing import Optional

# Add api directory to path for imports
api_dir = Path(__file__).parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from brain_loader import load_brain_memory
from chat import chat_completion, chat_completion_with_image
from cognitive_friction_engine import (
    analyze_cognitive_friction,
    CognitiveFrictionInput,
    CognitiveFrictionResult
)
from psychology_engine import (
    analyze_psychology,
    PsychologyAnalysisInput,
    PsychologyAnalysisResult
)
from rewrite_engine import rewrite_text
from models.rewrite_models import RewriteInput, RewriteOutput
from dataset_upload import router as dataset_router
from visual_trust_engine import analyze_visual_trust_from_path
from api.routes.image_trust import router as image_trust_router

# Load environment variables
# Try loading from project root .env file
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
else:
    load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Nima AI Brain API", version="1.0.0")

# Add CORS middleware
# Production: allow frontend domains
# Development: allow localhost for local testing
origins = [
    "https://nimasaraeian.com",
    "https://www.nimasaraeian.com",
    "http://localhost:3000",  # DEV: local development
    "http://127.0.0.1:3000",  # DEV: local development
    "http://localhost:8000",  # DEV: local development
    "http://127.0.0.1:8000",  # DEV: local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(dataset_router)
app.include_router(image_trust_router)

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
    
    logger = logging.getLogger("brain")
    MIN_TEXT_LENGTH = 0  # عملاً بی‌اثر، فقط می‌گذاریم اگر بعداً خواستی هشدار بدهی
    
    # Image debug variables
    has_image = False
    image_filename = None
    image_size_bytes = 0
    
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
            body = await request.json()
            print(f"[/api/brain] JSON request received")
            
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
                
                logger.warning("📸 Image received: filename=%s, size=%d bytes", image_filename, image_size_bytes)
                logger.warning("🔍 First 50 bytes: %s", image_data[:50])
                
                # Reset file cursor for further processing
                image.file = io.BytesIO(image_data)
                
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
                    
                    logger.warning("📸 Image received from form_data: filename=%s, size=%d bytes", image_filename, image_size_bytes)
                    logger.warning("🔍 First 50 bytes: %s", image_data[:50])
                    
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
                    image_mime = image_file.content_type or "image/png"
                    print(f"[/api/brain] Image received: {image_filename}, type: {image_mime}, size: {image_size_bytes} bytes")
                else:
                    logger.warning("🚫 No image uploaded in this request")
                    image_base64 = None
                    image_mime = None
        
        # تنها حالت غیرمجاز: نه متن، نه تصویر
        if not content_processed and not image_base64:
            raise HTTPException(
                status_code=400,
                detail="No content or image provided. Please upload a screenshot or paste the landing page/ad copy text."
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
            response_text = chat_completion_with_image(
                user_message=content_processed,  # ممکن است خالی باشد
                image_base64=image_base64,
                image_mime=image_mime,
                model="gpt-4o-mini",
                temperature=0.7
            )
            print(f"[/api/brain] Received response, length: {len(response_text) if response_text else 0}")
            if response_text:
                print(f"[/api/brain] Response preview: {response_text[:200]}...")
        except Exception as api_error:
            # Catch API errors separately to provide better error messages
            print(f"⚠️ OpenAI API error: {type(api_error).__name__}: {api_error}")
            import traceback
            traceback.print_exc()
            error_msg = "Failed to get response from AI model. Please try again."
            return BrainResponse(
                response=f"Error: {error_msg}",
                model="gpt-4o-mini",
                quality_score=0,
                quality_checks={"error": True, "error_type": "api_error"}
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

        # Build response with image_debug
        result = {
            "response": response_text,
            "model": "gpt-4o-mini",
            "quality_score": quality_score,
            "quality_checks": quality_checks,
            "image_debug": {
                "has_image": has_image,
                "image_filename": image_filename,
                "image_size_bytes": image_size_bytes,
            }
        }
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ ERROR in brain_endpoint: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        # Return error in BrainResponse format to maintain API contract
        # Clean error message to avoid exposing internal JSON parsing errors
        error_message = str(e) if str(e) else "Internal error while analyzing content."
        
        # Check if this is a JSON parsing error and provide a user-friendly message
        if "JSON" in error_message or "json" in error_message.lower() or "No number after minus sign" in error_message or "minus sign" in error_message.lower():
            print(f"⚠️ Detected JSON parsing error pattern: {error_message[:100]}")
            error_message = "Model response format error. The AI returned an unexpected format (possibly markdown or bullet points instead of JSON). Please try again."
        
        return BrainResponse(
            response=f"Error: {error_message}. Please try again later or contact support if the issue persists.",
            model="gpt-4o-mini",
            quality_score=0,
            quality_checks={"error": True, "error_type": type(e).__name__}
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
async def cognitive_friction_endpoint(input_data: CognitiveFrictionInput):
    """
    Cognitive Friction & Decision Psychology Analysis Endpoint
    
    Analyzes content for cognitive friction, trust, emotional clarity, 
    motivation alignment, and decision probability.
    
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
    try:
        result = analyze_cognitive_friction(input_data)
        return result
    except Exception as e:
        print(f"\n❌ ERROR in cognitive_friction_endpoint: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
    text: str = Form(..., description="Ad or landing page text to analyze"),
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
    """
    # Step 1: Run text-only psychology analysis using existing engine
    input_data = PsychologyAnalysisInput(
        raw_text=text,
        platform="visual_ad_or_landing",
        goal=["conversion"],
        audience="general",
        language="auto",
        meta={},
    )

    try:
        base_result = analyze_psychology(input_data)
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
        from uuid import uuid4

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



