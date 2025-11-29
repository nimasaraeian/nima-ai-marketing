"""
FastAPI application with AI brain system prompt
"""
from fastapi import FastAPI, HTTPException
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

# Load system prompt at startup
SYSTEM_PROMPT = load_brain_memory()


class ChatRequest(BaseModel):
    message: str
    model: str = "gpt-4"
    temperature: float = 0.7


class ChatResponse(BaseModel):
    response: str
    model: str


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Nima AI Brain API",
        "system_prompt_loaded": len(SYSTEM_PROMPT) > 0
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Chat endpoint using AI brain system prompt.
    
    The system prompt is automatically loaded from:
    - ai_brain/core_brain.md
    - ai_brain/memory_nima.md
    - ai_brain/memory_domain.md
    - ai_brain/memory_actions.md
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
    """Health check endpoint"""
    return {"status": "healthy"}

