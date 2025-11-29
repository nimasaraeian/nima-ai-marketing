"""
FastAPI application with AI brain system prompt - Main entry point

Deployment:
  For Render or similar services, use:
  uvicorn api.main:app --host 0.0.0.0 --port $PORT
  
  Module path: api.main:app
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# Add api directory to path for imports
api_dir = Path(__file__).parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from brain_loader import load_brain_memory
from chat import chat_completion
from cognitive_friction_engine import (
    analyze_cognitive_friction,
    CognitiveFrictionInput,
    CognitiveFrictionResult
)
from rewrite_engine import rewrite_text
from models.rewrite_models import RewriteInput, RewriteOutput

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
def brain_endpoint(request: BrainRequest):
    """
    Brain endpoint for marketing strategy queries.
    Accepts structured requests with role, locale, city, industry, channel, and query.
    """
    try:
        # Build the full query with context
        full_query = f"""Context:
- Role: {request.role}
- Locale: {request.locale}
- City: {request.city}
- Industry: {request.industry}
- Channel: {request.channel}

Query: {request.query}"""

        # Logging
        print("\n" + "=" * 60)
        print("=== NIMA TEST REQUEST ===")
        request_data = {
            "role": request.role,
            "locale": request.locale,
            "city": request.city,
            "industry": request.industry,
            "channel": request.channel,
            "query": request.query
        }
        print(request_data)
        
        print("\n=== SYSTEM PROMPT USED ===")
        print(SYSTEM_PROMPT[:500])
        print("...")
        print(f"(Total length: {len(SYSTEM_PROMPT)} characters)")
        
        print("\n=== QUALITY ENGINE STATUS ===")
        print(f"Quality Engine Active: {QUALITY_ENGINE_ENABLED}")
        print("=" * 60 + "\n")

        # Get response
        response_text = chat_completion(
            user_message=full_query,
            model="gpt-4o-mini",
            temperature=0.7
        )

        # Quality checks
        quality_checks = {
            "has_examples": any(keyword in response_text.lower() for keyword in ["headline", "hook", "مثال", "example", '"', '«']),
            "has_localization": any(keyword in response_text.lower() for keyword in [request.city.lower(), "istanbul", "استانبول", "tourist", "local", "گردشگر", "محلی"]),
            "has_action_plan": any(keyword in response_text.lower() for keyword in ["0-7", "7-30", "action", "برنامه", "اقدام"]),
            "has_metrics": any(keyword in response_text for keyword in ["%", "درصد", "ctr", "cpc", "cvr"]),
            "has_analysis": any(keyword in response_text.lower() for keyword in ["علت", "cause", "مشکل", "problem", "ریشه"])
        }
        
        quality_score = sum(quality_checks.values())

        return BrainResponse(
            response=response_text,
            model="gpt-4o-mini",
            quality_score=quality_score,
            quality_checks=quality_checks
        )
    except Exception as e:
        print(f"\n❌ ERROR in brain_endpoint: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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



