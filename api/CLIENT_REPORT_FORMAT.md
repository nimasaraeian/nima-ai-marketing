# Client-Ready Decision Report Format v1.0

## Overview

The Client-Ready Decision Report Format transforms raw decision analysis into a clear, structured, client-ready decision report that communicates insight, confidence, and action — without overwhelming or sounding generic.

**Core Principle:** Insight must come before recommendation. Diagnosis must come before action.

## API Endpoint

### POST `/api/brain/decision-engine/report`

Returns a formatted, client-ready decision report with 7 structured sections.

**Request:**
```json
{
  "content": "Landing page content or URL",
  "url": "https://example.com/pricing",
  "channel": "generic_saas"
}
```

**Query Parameters:**
- `format` (optional): `"markdown"` (default) or `"json"`

**Response (Markdown format):**
```json
{
  "report": "# Decision Analysis Report\n\n...",
  "format": "markdown"
}
```

**Response (JSON format):**
```json
{
  "report": "# Decision Analysis Report\n\n...",
  "raw_analysis": {
    "decision_blocker": "Outcome Unclear",
    "why": "...",
    "where": "CTA",
    "what_to_change_first": "...",
    "expected_decision_lift": "Medium (+10–25%)"
  },
  "context": {
    "url": "https://example.com",
    "platform": "generic"
  }
}
```

## Report Structure

Every analysis is rendered using the following sections in this exact order:

### 1️⃣ Executive Decision Summary

**Purpose:** Let a founder understand the problem in 30 seconds.

**Format:**
- What is blocking the decision
- How confident we are
- What category of fix matters most

**Example:**
```
The primary reason users hesitate is Outcome Unclear, with an estimated confidence of 75%.

This indicates a cognitive failure rather than a surface-level CTA issue.

[Brief explanation of the issue]
```

### 2️⃣ Context Snapshot

**Purpose:** Explain why the engine reached this conclusion.

**Includes:**
- Business type
- Price level
- Decision depth
- User intent stage
- Context confidence (explicit / inferred)

### 3️⃣ Decision Failure Breakdown

**Purpose:** Explain how the user's mind is working.

**For each outcome:**
- What breaks psychologically
- How it shows up in behavior
- How it interacts with context

**If a secondary outcome exists:** Explains interaction, not just listing.

### 4️⃣ What To Fix First

**Purpose:** Prevent random execution.

**Must include:**
- Name the first intervention priority
- Explain why this comes before others
- Warn what happens if it's ignored

**Note:** No tactics yet, only decision logic.

### 5️⃣ Actionable Recommendations

**Purpose:** Turn diagnosis into action.

**Grouped as:**
- Message-level changes
- Structure-level changes
- Timing / flow changes (only if relevant)

**Each recommendation must explicitly reference the outcome it addresses.**

### 6️⃣ What This Will Improve

**Purpose:** Help the client understand why this matters.

**Must include:**
- Describe expected behavioral improvement
- Avoid hard guarantees
- Use directional language

**Example framing:**
```
These changes are expected to reduce hesitation caused by [Outcome] and make the decision feel safer / clearer / lighter.
```

### 7️⃣ Next Diagnostic Step

**Purpose:** Position you as a long-term decision partner.

**Examples:**
- Deeper user intent analysis
- Journey-level decision mapping
- Cross-page consistency check

**Note:** Do NOT upsell aggressively. Keep it strategic.

## Language & Tone Rules

- **Calm, diagnostic, professional**
- **No hype, no buzzwords**
- **No "AI says"**
- **No absolutes**
- The report should feel like it was written by a senior behavioral strategist, not a model

## Formatting Constraints

- Clear section headers
- Short paragraphs
- Bullet points only where useful
- Readable for non-technical founders

## Success Criteria

After this step:
- ✅ The output can be sent directly to a client
- ✅ Founders understand what's wrong and what to do first
- ✅ Recommendations feel tailored, not templated
- ✅ You can confidently charge for the diagnosis alone

## Usage Example

```python
from api.decision_engine import DecisionEngineInput
from api.utils.client_report_formatter import format_decision_report

# Get decision analysis
input_data = DecisionEngineInput(
    content="https://example.com/pricing",
    url="https://example.com/pricing"
)

# Format as client-ready report
decision_output = analyze_decision_failure(input_data)
report = format_decision_report(
    decision_output.dict(),
    context_data={"url": "https://example.com/pricing"}
)

print(report)
```

## Implementation

The formatter is implemented in:
- `api/utils/client_report_formatter.py` - Core formatting logic
- `api/decision_engine.py` - API endpoint integration

## Integration with Decision Engine

The report formatter uses the same analysis from `/api/brain/decision-engine` but formats it for client delivery. The underlying analysis logic remains unchanged.






























