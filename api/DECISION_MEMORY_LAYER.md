# Decision Memory Layer v1.0

## Overview

The Decision Memory Layer enables the Decision Brain to remember, compare, and reason across multiple decision moments over time, turning isolated analyses into a longitudinal decision intelligence system.

**Core Principle:** Decisions are cumulative, not isolated. The engine must reason about decision history, not just snapshots.

## Architecture

### Components

1. **DecisionMemoryLayer** (`api/utils/decision_memory_layer.py`)
   - Enhanced memory storage and analysis
   - Trajectory analysis
   - Fatigue detection
   - Trust dynamics tracking

2. **Integration** (`api/decision_engine.py`)
   - Memory-aware outcome selection
   - Confidence adjustment
   - Repeated fix suppression
   - History insight generation

3. **Report Formatting** (`api/utils/client_report_formatter.py`)
   - Decision History Insight section
   - Fatigue analysis display
   - Trust dynamics reporting

## Memory Model

### Historical Outcome Log

For each prior analysis, the system stores:

- **Primary outcome** (decision blocker)
- **Secondary outcome** (if any)
- **Confidence scores** (0-100)
- **Timestamp** (when analysis occurred)
- **Location** (where on page)
- **What to change** (recommended fix)
- **Expected lift** (conversion improvement estimate)
- **URL** (context identifier)

**Key Rules:**
- ✅ Do NOT average outcomes
- ✅ Preserve sequence
- ✅ Maintain chronological order

### Context Identification

Memory is organized by **context_id**, which can be:
- URL (most common)
- User ID
- Session ID
- Brand/domain identifier

## Features

### 1. Outcome Trajectory Analysis

Analyzes how outcomes change over time:

- **Persistent:** Same outcome repeated (70%+ of analyses)
- **Weakening:** Outcome appears less frequently (40-70%)
- **Shifting:** Outcome changes to different type
- **Resolved:** Outcome no longer appears
- **Emerging:** New outcome appears

**Example:**
```
"Outcome Unclear persists across 5 analyses, indicating a structural 
issue that hasn't been addressed."
```

### 2. Decision Fatigue Detection

Detects when users experience repeated cognitive barriers:

**Indicators:**
- Repeated Cognitive Overload (Effort Too High 3+ times)
- Repeated Outcome Unclear (3+ times)
- No resolution despite exposure (same issue 4+ times)

**Fatigue Levels:**
- **None:** No fatigue patterns
- **Low:** Minor repetition
- **Medium:** Moderate fatigue (3-4 repeats)
- **High:** Significant fatigue (4-5 repeats)
- **Critical:** Severe fatigue (6+ repeats)

**Recommendations:**
- Critical: Complete decision architecture redesign
- High: Deeper structural interventions
- Medium: Comprehensive fixes addressing root causes

### 3. Trust Accumulation vs Erosion

Tracks trust dynamics over time:

**Trends:**
- **Decreasing:** Trust debt reducing (improving)
- **Increasing:** Trust debt growing (worsening)
- **Stable:** Trust issues consistent

**Consistency:**
- **Consistent:** Trust issues appear consistently
- **Inconsistent:** Trust issues appear/disappear (credibility sequence needed)
- **Improving:** Trust issues reducing over time

**Recommendations:**
- If increasing: Implement credibility sequencing strategy
- If inconsistent: Maintain consistent trust signals across touchpoints

### 4. Memory-Aware Outcome Selection

When memory exists, the system:

**Adjusts Confidence:**
- Sparse memory → lower confidence
- Consistent patterns → higher confidence
- Conflicting signals → explicit uncertainty

**Suppresses Repeated Fixes:**
- Detects if similar fix was attempted before
- Suggests alternative intervention approach
- Prevents repeating ineffective solutions

**Elevates Unresolved Root Causes:**
- Identifies persistent structural issues
- Prioritizes root causes over symptoms
- Recommends deeper interventions for chronic problems

## Output: Decision History Insight

When memory exists, every report includes a new section:

### Section 7: Decision History Insight

**What Has Already Failed:**
- Outcomes that appeared but didn't resolve
- Fixes that were attempted without success

**What Has Improved:**
- Outcomes that were resolved
- Issues that no longer appear

**What Remains Unresolved:**
- Persistent patterns across analyses
- Structural barriers that continue

**Why Users Are Still Hesitating:**
- Explanation based on history
- Fatigue analysis if applicable
- Trust dynamics if relevant

**Trajectory Summary:**
- Overall pattern direction
- Persistent vs shifting outcomes

**Fatigue Analysis (if applicable):**
- Fatigue level
- Indicators
- Recommendations

**Trust Dynamics (if applicable):**
- Trust debt trend
- Consistency assessment
- Credibility sequencing recommendations

## Memory Confidence Rules

### Sparse Memory → Low Confidence

When history is limited (< 3 analyses):
- Confidence adjusted downward (×0.9)
- Explicit note: "Limited history available"

### Consistent Patterns → Higher Confidence

When same outcome appears 3+ times:
- Confidence adjusted upward (×1.1, max 100%)
- Note: "Consistent pattern detected"

### Conflicting Signals → Explicit Uncertainty

When recent outcomes differ from proposed:
- Confidence adjusted downward (×0.85)
- Note: "Conflicting signals detected"

## Usage

### Automatic Integration

The memory layer is automatically integrated into the decision engine:

```python
# Decision engine automatically:
# 1. Checks memory before analysis
# 2. Adjusts confidence based on history
# 3. Suppresses repeated fixes
# 4. Generates history insight
# 5. Saves new analysis to memory

result = analyze_decision_failure(input_data)
# result.decision_history_insight contains history analysis
```

### Programmatic Access

```python
from utils.decision_memory_layer import decision_memory_layer

# Get history
history = decision_memory_layer.get_history("https://example.com")

# Analyze trajectory
trajectories = decision_memory_layer.analyze_trajectory("https://example.com")

# Detect fatigue
fatigue = decision_memory_layer.detect_fatigue("https://example.com")

# Analyze trust dynamics
trust = decision_memory_layer.analyze_trust_dynamics("https://example.com")
```

## API Response

The decision engine output now includes:

```json
{
  "decision_blocker": "Outcome Unclear",
  "why": "...",
  "where": "CTA",
  "what_to_change_first": "...",
  "expected_decision_lift": "Medium (+10–25%)",
  "decision_history_insight": {
    "what_failed": ["Trust Gap (appeared 3 times, persistent)"],
    "what_improved": ["Risk Not Addressed (resolved)"],
    "what_remains_unresolved": ["Outcome Unclear (persists across 5 analyses)"],
    "why_still_hesitating": "Decision fatigue: ...",
    "trajectory_summary": "Persistent patterns: Outcome Unclear...",
    "fatigue": {
      "level": "high",
      "indicators": ["Repeated cognitive overload (4 times)"],
      "recommendation": "..."
    },
    "trust_dynamics": {
      "trend": "increasing",
      "consistency": "inconsistent",
      "recommendation": "..."
    }
  }
}
```

## Success Criteria

After this layer:

✅ **Repeated analyses feel dramatically different**  
✅ **The engine stops repeating itself**  
✅ **Clients get answers to "why nothing changes"**  
✅ **You outperform every static CRO tool**

## Implementation Details

### Storage

- **In-memory storage** (default)
- Can be extended to persistent storage (database, file)
- Max 50 items per context (configurable)

### Performance

- Memory operations are O(n) where n = history length
- Trajectory analysis: O(n log n) for sorting
- Fatigue detection: O(n) for counting
- Trust analysis: O(n) for trend calculation

### Limitations

- Memory is per-process (not shared across instances)
- For production, consider persistent storage
- Context identification relies on URL (can be enhanced)

## Future Enhancements

1. **Persistent Storage:** Database integration for cross-session memory
2. **User-Level Memory:** Track decisions across different URLs for same user
3. **Brand-Level Memory:** Aggregate insights across all pages for a brand
4. **Advanced NLP:** Better similarity detection for repeated fixes
5. **Predictive Analysis:** Predict likely outcomes based on history

## Notes

- Memory layer is optional (graceful fallback if not available)
- Backward compatible with existing decision engine
- Legacy memory store still maintained for compatibility
- History insight only appears when memory exists


















