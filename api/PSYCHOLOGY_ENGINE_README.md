# CORE PSYCHOLOGY ENGINE - NIMA MARKETING BRAIN

## Overview

The CORE PSYCHOLOGY ENGINE is a comprehensive 13-pillar psychological analysis system that evaluates any marketing content using fundamental psychological principles.

## The 13 Psychology Pillars

1. **Cognitive Friction** - Mental effort required to understand or process the text
2. **Emotional Resonance** - Emotional alignment between message and user's feeling state
3. **Trust & Clarity** - Trustworthiness, transparency, and believability
4. **Decision Simplicity** - Ease of choosing the next step
5. **Motivation Profile** - Alignment with Self-Determination Theory (Autonomy, Competence, Relatedness)
6. **Behavioral Biases** - Detection and analysis of cognitive biases
7. **Personality Fit** - Alignment with personality-driven communication preferences
8. **Value Perception** - How much value the message communicates
9. **Attention Architecture** - Structure for capturing and holding attention
10. **Narrative Clarity** - Story flow and structure (hook → conflict → value → proof → CTA)
11. **Emotional Safety** - Psychological safety and comfort
12. **Actionability** - Ability to generate immediate action
13. **Identity Alignment** - Fit with user's self-identity

## API Endpoint

### POST `/api/brain/psychology-analysis`

Analyzes content using all 13 psychological pillars.

#### Request Body

```json
{
  "raw_text": "Your marketing content here...",
  "platform": "landing_page",  // Optional: landing_page, instagram, linkedin, email, etc.
  "goal": ["leads", "sales"],   // Optional: clicks, leads, sales, engagement, etc.
  "audience": "cold",            // Optional: cold, warm, retargeting, etc.
  "language": "en",              // Optional: en, tr, fa, etc.
  "meta": null                   // Optional: any additional metadata
}
```

#### Response

```json
{
  "analysis": {
    "cognitive_friction": {
      "score": 45,
      "signals": ["Long sentences detected", "Abstract wording"],
      "issues": ["Missing context", "Logical jumps"],
      "explanation": "The content requires moderate mental effort...",
      "rewrite": "Improved version..."
    },
    "emotional_resonance": {
      "score": 72,
      "emotion_detected": "Hope",
      "emotion_needed": "Trust",
      "mismatch_report": "Content triggers hope but needs more trust signals",
      "rewrite": "Improved version..."
    },
    // ... all 13 pillars
  },
  "overall": {
    "global_score": 65,
    "top_problems": ["Low trust signals", "Weak CTA"],
    "top_strengths": ["Good emotional resonance", "Clear value proposition"],
    "final_recommendations": ["Add social proof", "Strengthen guarantee"]
  },
  "human_readable_report": "Full formatted report..."
}
```

## Usage Examples

### Python

```python
from psychology_engine import analyze_psychology, PsychologyAnalysisInput

input_data = PsychologyAnalysisInput(
    raw_text="Your marketing copy here...",
    platform="landing_page",
    goal=["leads"],
    audience="cold",
    language="en"
)

result = analyze_psychology(input_data)

# Access results
print(f"Global Score: {result.overall['global_score']}")
print(f"Cognitive Friction: {result.analysis['cognitive_friction']['score']}")
print(result.human_readable_report)
```

### cURL

```bash
curl -X POST "http://localhost:8000/api/brain/psychology-analysis" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Your marketing content here...",
    "platform": "landing_page",
    "goal": ["leads", "sales"],
    "audience": "cold",
    "language": "en"
  }'
```

### JavaScript/Fetch

```javascript
const response = await fetch('http://localhost:8000/api/brain/psychology-analysis', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    raw_text: 'Your marketing content here...',
    platform: 'landing_page',
    goal: ['leads', 'sales'],
    audience: 'cold',
    language: 'en'
  })
});

const result = await response.json();
console.log('Global Score:', result.overall.global_score);
console.log('Report:', result.human_readable_report);
```

## Testing

Run the test script:

```bash
cd api
python test_psychology_engine.py
```

This will:
- Test the analysis with sample content
- Display pillar scores
- Show the human-readable report
- Save full JSON results to `test_psychology_result.json`

## Key Features

- **Never Skips Pillars**: All 13 pillars are always analyzed
- **Comprehensive Scoring**: Each pillar scored 0-100 with detailed explanations
- **Actionable Rewrites**: Improved versions for each pillar
- **Dual Output**: Both structured JSON and human-readable report
- **Psychological Rigor**: Based on established psychological frameworks
- **Deterministic**: Consistent analysis using validated models

## Output Structure

Each pillar analysis includes:
- **Score** (0-100): Quantitative assessment
- **Signals/Issues**: Specific problems detected
- **Explanation**: Why this score was assigned
- **Rewrite**: Improved version optimized for this pillar

The overall summary provides:
- **Global Score**: Weighted average across all pillars
- **Top Problems**: Most critical issues to fix
- **Top Strengths**: What's working well
- **Final Recommendations**: Actionable next steps

## Integration

The psychology engine integrates seamlessly with:
- Existing cognitive friction engine
- Rewrite engine
- Main NIMA Marketing Brain system

All endpoints are available through the FastAPI application at `/api/brain/psychology-analysis`.

## Requirements

- Python 3.8+
- OpenAI API key (set in `.env` as `OPENAI_API_KEY`)
- FastAPI
- Pydantic

## Notes

- The engine uses GPT-4o for comprehensive analysis
- Temperature is set to 0.3 for consistent, deterministic results
- JSON mode is enforced to ensure structured output
- Fallback handling ensures graceful error recovery

