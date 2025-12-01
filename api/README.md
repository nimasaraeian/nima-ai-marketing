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

## Visual Trust Model Integration (Optional)

You can optionally enable a **visual trust layer** that scores ad / landing page images as:
`high_trust`, `medium_trust`, or `low_trust` and feeds this into the Decision Psychology report.

### 1. Train the visual trust model

1. Prepare your dataset:

   ```text
   dataset/
     images/
       high_trust/
       medium_trust/
       low_trust/
   ```

2. Train the model (from project root):

   ```bash
   python training/train_visual_trust_model.py
   ```

   This will save:

   - `models/visual_trust_model.keras`
   - `models/visual_trust_class_names.txt`

### 2. Use the text + image endpoint

Once the model is trained and the FastAPI server is running, you can call:

- `POST /api/brain/analyze-with-image`
- (alias) `POST /api/brain/psychology-analysis-with-image`

Both endpoints accept `multipart/form-data` with fields:

- `text` (string, required): ad or landing page copy
- `image` (file, optional): screenshot or creative for visual trust analysis

Example `curl` request:

```bash
curl -X POST "http://localhost:8000/api/brain/analyze-with-image" \
  -H "Accept: application/json" \
  -F "text=This is my ad copy for a new landing page..." \
  -F "image=@/path/to/landing_screenshot.png"
```

The response extends the standard psychology analysis with:

- `visual_trust`: a compact summary
  - `label`: `"high_trust" | "medium_trust" | "low_trust"`
  - `score_numeric`: simple numeric score (e.g. 80/50/20)
  - `scores`: per-class probabilities

- `visual_layer`: a structured section for the Decision Psychology Report
  - `visual_trust_label`
  - `visual_trust_score`
  - `visual_trust_breakdown`
  - `visual_comment` (short, rule-based interpretation)

