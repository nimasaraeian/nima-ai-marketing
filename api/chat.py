"""
Chat API endpoint - Uses AI brain memory as system prompt
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from api.brain_loader import load_brain_memory

# Load .env file
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

# Initialize OpenAI client lazily
_client = None

def get_client():
    """Get or create OpenAI client (lazy initialization)"""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Try reading directly from .env file
            if env_file.exists():
                try:
                    with open(env_file, 'r', encoding='utf-8-sig') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and 'OPENAI_API_KEY' in line:
                                if '=' in line:
                                    key, value = line.split('=', 1)
                                    key = key.strip()
                                    value = value.strip()
                                    if key == 'OPENAI_API_KEY':
                                        # Remove quotes
                                        if value.startswith('"') and value.endswith('"'):
                                            value = value[1:-1]
                                        elif value.startswith("'") and value.endswith("'"):
                                            value = value[1:-1]
                                        api_key = value
                                        break
                except Exception:
                    pass
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        # Set timeout to 300 seconds (5 minutes) for long-running requests
        _client = OpenAI(api_key=api_key, timeout=300.0, max_retries=3)
    return _client

# Load system prompt once at startup
SYSTEM_PROMPT = load_brain_memory()

def reload_system_prompt():
    """Reload the system prompt (useful for development/testing)"""
    global SYSTEM_PROMPT
    from brain_loader import clear_cache
    clear_cache()
    SYSTEM_PROMPT = load_brain_memory()
    return SYSTEM_PROMPT


def chat_completion(user_message, model="gpt-4", temperature=0.7):
    """
    Send a chat message using the AI brain system prompt.
    
    Args:
        user_message: The user's message
        model: OpenAI model to use (default: gpt-4)
        temperature: Temperature for response (default: 0.7)
    
    Returns:
        str: Assistant's response
    """
    client = get_client()
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    
    return response.choices[0].message.content


def chat_completion_with_image(
    user_message="",
    image_base64=None,
    image_mime=None,
    image_score=None,
    visual_only_mode: bool = False,
    model="gpt-4o-mini",
    temperature=0.7,
):
    """
    Send a chat message with optional image using the AI brain system prompt.
    Supports text-only, image-only, or both.
    
    Args:
        user_message: The user's text message (can be empty if image is provided)
        image_base64: Optional base64-encoded image string
        image_mime: Optional MIME type of the image (e.g., "image/png", "image/jpeg")
        image_score: Optional numeric score (0-100) from local image model analysis
        model: OpenAI model to use (default: gpt-4o-mini)
        temperature: Temperature for response (default: 0.7)
    
    Returns:
        str: Assistant's response
    """
    client = get_client()
    
    # Build image context if image_score is provided
    image_context = ""
    if image_score is not None:
        # Derive a simple qualitative label from the numeric score
        if image_score >= 80:
            image_label = "strong / high-performing visual"
        elif image_score >= 50:
            image_label = "average / acceptable visual"
        else:
            image_label = "weak / low-performing visual"
        
        image_context = (
            f"\n\n[IMAGE ANALYSIS INPUT]\n"
            f"- image_score (0–100): {image_score:.1f}\n"
            f"- qualitative_label: {image_label}\n"
            f"Use this as a signal of how effective the uploaded marketing visual is.\n"
            f"If image_score is low, you must give specific, practical suggestions to improve the image (layout, text hierarchy, contrast, clarity of CTA, emotional impact, etc.)."
        )

    # Build mode context and override base_content when in visual_only_mode
    if visual_only_mode:
        # Override base content: we don't have text, only a visual.
        base_content = (
            "VISUAL_ONLY_MODE\n\n"
            "The user did NOT provide raw text. They have submitted a screenshot/visual of a landing page.\n"
            "You are in pure visual analysis mode.\n"
            "- DO NOT say that 'no content was provided' or that 'the page has no information'.\n"
            "- Assume the landing page DOES have real content, but you only see its visual layout.\n"
            "- Use the given image_score (0–100) as the main indicator of visual strength.\n"
            "- Analyze layout, visual hierarchy, CTA visibility, trust signals, clarity of the hero section, and emotional impact.\n"
            "- You may still produce a Decision Friction Score, but base it on visual effectiveness, not on 'missing text'.\n"
        )
    else:
        base_content = user_message or ""

    # Build final user content from base_content + image_context
    user_content_text = base_content + (image_context or "")
    
    # Build user content array conditionally
    user_content = []
    
    # Add text only if content exists
    if user_content_text.strip():
        user_content.append({"type": "text", "text": user_content_text})
    
    # Add image if provided
    if image_base64 and image_mime:
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{image_mime};base64,{image_base64}"
            }
        })
    
    # Fallback: if both are empty, use a default message
    if not user_content:
        user_content = [{"type": "text", "text": "Analyze this content."}]
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    
    return response.choices[0].message.content


# Example usage (for testing)
if __name__ == "__main__":
    test_message = "What's my core expertise in AI marketing?"
    response = chat_completion(test_message)
    print("Response:", response)

