"""
Chat API endpoint - Uses AI brain memory as system prompt
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from brain_loader import load_brain_memory

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
        _client = OpenAI(api_key=api_key)
    return _client

# Load system prompt once at startup
SYSTEM_PROMPT = load_brain_memory()


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


def chat_completion_with_image(user_message="", image_base64=None, image_mime=None, model="gpt-4o-mini", temperature=0.7):
    """
    Send a chat message with optional image using the AI brain system prompt.
    Supports text-only, image-only, or both.
    
    Args:
        user_message: The user's text message (can be empty if image is provided)
        image_base64: Optional base64-encoded image string
        image_mime: Optional MIME type of the image (e.g., "image/png", "image/jpeg")
        model: OpenAI model to use (default: gpt-4o-mini)
        temperature: Temperature for response (default: 0.7)
    
    Returns:
        str: Assistant's response
    """
    client = get_client()
    
    # Build user content array conditionally
    user_content = []
    
    # Add text only if content exists
    if user_message and user_message.strip():
        user_content.append({"type": "text", "text": user_message.strip()})
    
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

