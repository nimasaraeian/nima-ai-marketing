# Journey-Level Decision Engine v1.0

## Overview

The Journey-Level Decision Engine infers the mental decision stage of the user from the decision environment (page structure, CTA, offer type, risk level) — not from behavioral tracking — and uses this stage to judge whether each detected decision friction is natural or critical.

**Core Principle:** We do NOT track the user journey. We infer the decision stage from the decision context. Journey here means mental decision phase, not navigation history.

## Decision Stages

### 1️⃣ ORIENTATION

**User is trying to understand what this is.**

**Page Signals:**
- Educational tone
- "What is…", "How it works"
- No strong CTA
- No price expectation

**Decision Logic:**
- Friction is mostly natural
- Goal is guidance, not conversion

### 2️⃣ SENSE-MAKING

**User is checking relevance: Is this for me?**

**Page Signals:**
- Benefits explained
- Use cases
- Light persuasion
- "Learn more", "See how"

**Decision Logic:**
- Identity alignment matters
- Heavy CTAs are premature

### 3️⃣ EVALUATION

**User is comparing and weighing trade-offs.**

**Page Signals:**
- Pricing visibility
- Feature comparison
- FAQs
- Risk questions

**Decision Logic:**
- Risk & trust become critical
- Friction must be addressed

### 4️⃣ COMMITMENT

**User is close to action.**

**Page Signals:**
- "Buy", "Book", "Start trial"
- Strong CTAs
- Forms, checkout, booking

**Decision Logic:**
- Any unresolved friction is dangerous
- Small issues cause abandonment

### 5️⃣ POST-DECISION VALIDATION

**User seeks reassurance after action.**

**Page Signals:**
- Confirmation pages
- "What happens next"
- Onboarding copy

**Decision Logic:**
- Trust reinforcement required
- Regret prevention

## Stage Inference

The engine infers the stage using:

1. **CTA Language**
   - Orientation: "What is", "How it works"
   - Sense-Making: "Learn more", "See how"
   - Evaluation: "Compare", "See pricing"
   - Commitment: "Buy", "Sign up", "Start trial"
   - Post-Decision: "What happens next"

2. **Offer Commitment Level**
   - Low commitment (trial, demo) → Sense-Making/Commitment
   - High commitment (purchase, subscription) → Commitment

3. **Risk Level of Decision**
   - High risk → Evaluation/Commitment
   - Low risk → Orientation/Sense-Making

4. **Presence or Absence of Pricing**
   - Pricing visible → Evaluation/Commitment
   - No pricing → Orientation/Sense-Making

5. **Structural Cues**
   - Forms/checkout → Commitment
   - Comparison tables → Evaluation
   - Educational content → Orientation
   - Confirmation pages → Post-Decision

**Rules:**
- ❌ Do NOT ask for stage input
- ✅ Always infer from context

## Stage × Outcome Interaction Logic

The engine evaluates whether a detected Outcome is:

- ✅ **Natural** at this stage
- ✅ **Acceptable** at this stage
- ⚠️ **Warning** at this stage
- 🚨 **Critical** at this stage
- 🚨 **High Risk** at this stage

### Examples (Mandatory Logic)

| Outcome | Orientation | Sense-Making | Evaluation | Commitment | Post-Decision |
|---------|------------|--------------|------------|------------|---------------|
| **Trust Gap** | ✅ Natural | ✅ Acceptable | ⚠️ Warning | 🚨 Critical | 🚨 Critical |
| **Outcome Unclear** | ✅ Natural | ⚠️ Warning | 🚨 Critical | 🚨 High Risk | 🚨 Critical |
| **Risk Not Addressed** | ✅ Acceptable | ✅ Acceptable | 🚨 Critical | 🚨 High Risk | 🚨 High Risk |
| **Effort Too High** | ✅ Acceptable | ✅ Acceptable | ⚠️ Warning | 🚨 High Risk | ⚠️ Warning |
| **Commitment Anxiety** | ✅ Natural | ✅ Natural | ⚠️ Warning | 🚨 Critical | 🚨 Critical |

### Detailed Examples

**Trust Debt at ORIENTATION → ✅ Natural**
- Trust signals are not yet critical
- Users are still exploring
- Don't need full credibility yet

**Trust Debt at COMMITMENT → 🚨 Critical**
- Trust gaps cause immediate abandonment
- Users won't proceed without credibility

**Timing Friction at SENSE-MAKING → ✅ Natural**
- Some friction is expected when checking relevance
- Heavy CTAs would be premature

**Timing Friction at EVALUATION → ⚠️ Warning**
- Should be addressed to prevent progression issues

**Cognitive Overload at ORIENTATION → ✅ Acceptable**
- Users expect to invest effort in understanding
- Cognitive load is acceptable during learning

**Cognitive Overload at COMMITMENT → 🚨 High Risk**
- High cognitive effort causes abandonment
- Decision should feel simple and clear

## Output Modifications

The final report now includes:

### ✅ Decision Stage Assessment

**Section 7 in client-ready reports:**

- **Identified Decision Stage**
  - Which stage was inferred
  - Confidence level (0-100%)

- **Why the Environment Signals This Stage**
  - What signals led to this inference
  - Explanation of stage determination

- **Friction Severity Adjustment**
  - Which frictions are normal here
  - Which frictions require immediate fixing
  - Which frictions should be guided, not removed

### Friction Severity Recommendations

**Natural:**
- "This friction is natural at [stage] stage. Do NOT fix it. Focus on guidance and education instead."

**Acceptable:**
- "This friction is acceptable at [stage] stage. Consider gentle guidance rather than aggressive fixes."

**Warning:**
- "This friction should be addressed at [stage] stage. It may prevent progression to the next stage."

**Critical:**
- "This friction is CRITICAL at [stage] stage. It must be fixed immediately to prevent abandonment."

**High Risk:**
- "This friction is HIGHLY DANGEROUS at [stage] stage. It likely causes immediate abandonment. Fix urgently."

## Hard Constraints

- ❌ Do NOT recommend fixing every friction
- ❌ Do NOT push conversion at early stages
- ❌ Do NOT judge all frictions equally
- ❌ Do NOT assume buying intent everywhere

## Implementation

### Files

1. **`api/utils/decision_stage_inference.py`**
   - `DecisionStageInference` class
   - Stage inference logic
   - Friction severity assessment

2. **`api/decision_engine.py`** (modified)
   - Stage inference integration
   - Context signal extraction
   - Stage assessment in output

3. **`api/utils/client_report_formatter.py`** (modified)
   - Decision Stage Assessment section
   - Friction severity display

### API Response

```json
{
  "decision_blocker": "Trust Gap",
  "why": "...",
  "where": "CTA",
  "what_to_change_first": "...",
  "expected_decision_lift": "Medium (+10–25%)",
  "decision_stage_assessment": {
    "stage": "commitment",
    "confidence": 85.0,
    "signals": [
      "Commitment CTA language: 'Buy Now'",
      "Checkout/form present",
      "Pricing visible"
    ],
    "explanation": "Inferred commitment stage with 85% confidence based on: Commitment CTA language, Checkout/form present, Pricing visible",
    "friction_severity": "critical",
    "friction_reasoning": "Trust gaps at commitment are critical. Users won't proceed without sufficient credibility.",
    "friction_recommendation": "This friction is CRITICAL at commitment stage. It must be fixed immediately to prevent abandonment."
  }
}
```

## Success Criteria

After this engine:

✅ **The same friction produces different advice depending on stage**  
✅ **The system sometimes says: "This should NOT be fixed here"**  
✅ **Recommendations feel situational, not aggressive**  
✅ **Founders trust the logic more than generic CRO advice**

## Examples

### Example 1: Trust Gap at Orientation

**Stage:** Orientation  
**Outcome:** Trust Gap  
**Severity:** Natural

**Recommendation:**
"This friction is natural at orientation stage. Do NOT fix it. Focus on guidance and education instead."

### Example 2: Trust Gap at Commitment

**Stage:** Commitment  
**Outcome:** Trust Gap  
**Severity:** Critical

**Recommendation:**
"This friction is CRITICAL at commitment stage. It must be fixed immediately to prevent abandonment."

### Example 3: Outcome Unclear at Evaluation

**Stage:** Evaluation  
**Outcome:** Outcome Unclear  
**Severity:** Critical

**Recommendation:**
"This friction is CRITICAL at evaluation stage. It must be fixed immediately to prevent abandonment."

## Notes

- Stage inference is automatic (no user input required)
- Inference is based on context, not tracking
- Friction severity adjusts recommendations appropriately
- System respects natural friction at early stages
- Recommendations are stage-appropriate, not aggressive





















