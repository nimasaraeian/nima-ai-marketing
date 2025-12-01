"""
FastAPI application with AI brain system prompt - Main entry point

Deployment:
  For Render or similar services, use:
  uvicorn api.main:app --host 0.0.0.0 --port $PORT
  
  Module path: api.main:app
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import sys
import base64
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


@app.post("/api/brain", response_model=BrainResponse)
async def brain_endpoint(
    content: Optional[str] = Form(None, description="Text content to analyze (optional if image provided)"),
    image: Optional[UploadFile] = File(None, description="Optional image file")
):
    """
    Brain endpoint for marketing strategy queries.
    Accepts multipart/form-data with:
    - content (optional): Text content to analyze
    - image (optional): Image file for visual analysis
    
    At least one of content or image must be provided.
    """
    MIN_TEXT_LENGTH = 0  # عملاً بی‌اثر، فقط می‌گذاریم اگر بعداً خواستی هشدار بدهی
    
    try:
        # Log request info
        print("\n" + "=" * 60)
        print("=== NIMA BRAIN REQUEST ===")
        print(f"[/api/brain] has image? {image is not None}")
        
        # Process content
        content_processed = content.strip() if content else ""
        print(f"[/api/brain] content length: {len(content_processed)}")
        
        # تنها حالت غیرمجاز: نه متن، نه تصویر
        if not content_processed and not image:
            raise HTTPException(
                status_code=400,
                detail="No content or image provided. Please upload a screenshot or paste the landing page/ad copy text."
            )
        
        # آماده‌سازی تصویر (در صورت وجود)
        image_base64: Optional[str] = None
        image_mime: Optional[str] = None
        
        if image:
            # Read image file and convert to base64
            image_bytes = await image.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            image_mime = image.content_type or "image/png"
            print(f"[/api/brain] Image received: {image.filename}, type: {image_mime}, size: {len(image_bytes)} bytes")
        
        print("\n=== SYSTEM PROMPT USED ===")
        print(SYSTEM_PROMPT[:500])
        print("...")
        print(f"(Total length: {len(SYSTEM_PROMPT)} characters)")
        
        print("\n=== QUALITY ENGINE STATUS ===")
        print(f"Quality Engine Active: {QUALITY_ENGINE_ENABLED}")
        print("=" * 60 + "\n")

        # Get response (supports text-only, image-only, or both)
        response_text = chat_completion_with_image(
            user_message=content_processed,  # ممکن است خالی باشد
            image_base64=image_base64,
            image_mime=image_mime,
            model="gpt-4o-mini",
            temperature=0.7
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

        return BrainResponse(
            response=response_text,
            model="gpt-4o-mini",
            quality_score=quality_score,
            quality_checks=quality_checks
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ ERROR in brain_endpoint: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        # Return error in BrainResponse format to maintain API contract
        error_message = str(e) if str(e) else "Internal error while analyzing content."
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

        print(f"\n❌ ERROR in psychology_analysis_with_image (text analysis): {type(e).__name__}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Text analysis failed: {e}")

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
            with tmp_path.open("wb") as buffer:
                content = await image.read()
                buffer.write(content)

            vt = analyze_visual_trust_from_path(str(tmp_path))

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
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            import traceback

            print(f"\n❌ ERROR in psychology_analysis_with_image (visual analysis): {type(e).__name__}: {e}")
            traceback.print_exc()
            # We don't want to lose the text analysis result if visual fails
            visual_trust = {"error": str(e)}
            visual_layer = None
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



