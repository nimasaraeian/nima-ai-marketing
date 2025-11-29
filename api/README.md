# AI Brain API

This API uses the AI brain memory files as system prompts for LLM interactions.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY=your_api_key_here
```

Or create a `.env` file:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

The `brain_loader.py` module automatically loads and caches all memory files from `ai_brain/` folder:
- `core_brain.md`
- `memory_nima.md`
- `memory_domain.md`
- `memory_actions.md`

These are concatenated into a single system prompt that's used for all LLM calls.

## Example

```python
from api.chat import chat_completion

response = chat_completion("What's my expertise?")
print(response)
```

## Integration

Use `chat_completion()` function in:
- Website chat widgets
- Internal tools
- Public-facing AI services

The system prompt is loaded once at startup and cached for performance.

## FastAPI Server

Run the FastAPI server:

```bash
uvicorn app:app --reload
```

Then use the `/chat` endpoint:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is my expertise?", "model": "gpt-4"}'
```

Or use the interactive docs at: http://localhost:8000/docs

