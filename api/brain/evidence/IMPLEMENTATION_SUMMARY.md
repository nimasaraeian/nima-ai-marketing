# Decision Brain Evidence Extension - Implementation Summary

## Overview

Successfully extended the Decision Brain with Ad and Pricing evidence extraction while **preserving all existing landing page analysis logic**. The implementation is fully additive and modular.

## Files Created

### Core Structure
1. **`api/brain/decision_signals.py`**
   - `DecisionSignals` dataclass: Unified signal structure
   - All evidence extractors populate this structure
   - Fields: `promise_strength`, `emotional_tone`, `reassurance_level`, `risk_exposure`, `cognitive_load`, `pressure_level`

### Evidence Extractors
2. **`api/brain/evidence/landing_signals.py`**
   - `extract_landing_signals(features: PageFeatures) -> DecisionSignals`
   - Wraps existing `analyze_decision()` logic
   - Maps existing scores to DecisionSignals format
   - **Does NOT modify existing landing analysis**

3. **`api/brain/evidence/ad_signals.py`**
   - `extract_ad_signals(input_data: AdInput) -> DecisionSignals`
   - Extracts: promise strength, emotional tone, pressure level, reassurance level, expectation gap
   - Analyzes ad copy text (headline, description, body)
   - **Focus: Decision psychology only, NOT design quality**

4. **`api/brain/evidence/pricing_signals.py`**
   - `extract_pricing_signals(html: str, text: str) -> DecisionSignals`
   - Extracts: choice overload, transparency level, risk exposure, commitment pressure
   - Maps to DecisionSignals: `choice_overload → cognitive_load`, `transparency_level → reassurance_level`, `commitment_pressure → pressure_level`
   - **Focus: Decision psychology only, NOT pricing strategy**

### Signal Processing
5. **`api/brain/evidence/signal_merger.py`**
   - `merge_signals(landing, ad, pricing) -> (merged_signals, confidence)`
   - **Rules:**
     - Landing signals: 60% weight (baseline, highest trust)
     - Ad signals: 20% weight (adjusts intensity)
     - Pricing signals: 20% weight (adjusts intensity)
     - If signals conflict, confidence decreases
     - If signals agree, confidence increases

6. **`api/brain/evidence/explanation_builder.py`**
   - `build_evidence_explanation(merged_signals, ...) -> str`
   - Generates explanation text mentioning evidence sources
   - Example: "This assessment combines landing and ad evidence. The analysis shows high promise strength and low reassurance."

7. **`api/brain/evidence/integration.py`**
   - `EvidenceContext` class: Container for all evidence sources
   - `extract_all_evidence(context) -> dict`: Orchestrates extraction
   - `enrich_decision_output(output, evidence_result) -> dict`: Adds evidence metadata to decision output

### Documentation & Tests
8. **`api/brain/evidence/README.md`**
   - Usage guide with examples
   - Signal mapping documentation
   - Architecture overview

9. **`tests/test_evidence_modules.py`**
   - Unit tests for all extractors
   - Tests for signal merging
   - Tests for edge cases

## Key Design Decisions

### ✅ Preserved Existing Logic
- **No changes** to `api/brain/decision_brain.py`
- **No changes** to `api/decision_engine.py` core logic
- **No changes** to Decision State definitions
- Landing page analysis works exactly as before

### ✅ Additive Architecture
- New modules are **optional**
- Existing code continues to work without changes
- Evidence extraction can be added incrementally

### ✅ Signal Abstraction
- All evidence sources produce `DecisionSignals`
- Unified structure enables consistent merging
- Easy to add new evidence sources in the future

### ✅ Weighted Merging
- Landing signals are baseline (60% weight)
- Ad/Pricing adjust intensity (20% each)
- Confidence reflects signal agreement

## Integration Points

### Option 1: Direct Usage (Current)
```python
from api.brain.evidence.integration import EvidenceContext, extract_all_evidence

context = EvidenceContext(
    landing_features=page_features,
    ad_input=AdInput(ad_copy="..."),
    pricing_html=pricing_html
)

evidence_result = extract_all_evidence(context)
# Use evidence_result["merged_signals"] in your decision logic
```

### Option 2: Enrich Decision Output
```python
from api.brain.evidence.integration import enrich_decision_output

enriched = enrich_decision_output(
    decision_output=original_output,
    evidence_result=evidence_result
)
# enriched["evidence"] contains evidence metadata
```

### Option 3: Future Integration (Not Implemented)
- Add optional parameters to `DecisionEngineInput` for ad/pricing evidence
- Automatically extract and merge signals in decision engine
- Enrich explanations with evidence sources

## Output Structure

The enriched output includes an `evidence` section:

```json
{
  "decision_blocker": "Outcome Unclear",
  "why": "Original explanation...",
  "evidence": {
    "sources_used": ["landing", "ad", "pricing"],
    "explanation": "This assessment combines landing, ad, and pricing evidence...",
    "merged_signals": {
      "promise_strength": "high",
      "emotional_tone": "urgent",
      "reassurance_level": "medium",
      "risk_exposure": "low",
      "cognitive_load": "medium",
      "pressure_level": "high"
    },
    "confidence": 0.75
  }
}
```

## Constraints Met

✅ **DO NOT rewrite existing landing logic** - Preserved  
✅ **DO NOT change Decision State definitions** - Unchanged  
✅ **DO NOT add UX/CRO recommendations** - Decision signals only  
✅ **Only EXTEND the brain** - Fully additive  
✅ **Keep everything additive and modular** - Modular architecture  

## Testing

Run tests:
```bash
pytest tests/test_evidence_modules.py -v
```

## Next Steps (Optional)

1. **Wire into Decision Engine**: Add optional parameters to `DecisionEngineInput` for ad/pricing evidence
2. **Image Analysis**: Extend `extract_ad_signals` to analyze ad images (currently text-only)
3. **More Evidence Sources**: Add social proof, reviews, testimonials as separate evidence sources
4. **Confidence Calibration**: Fine-tune confidence scoring based on real-world validation

## Success Criteria

✅ Landing-only analysis works exactly as before  
✅ Adding Ad evidence enriches the decision explanation  
✅ Adding Pricing evidence increases confidence or highlights hesitation  
✅ Output remains ONE decision state, not multiple reports  
✅ All modules are modular and can be used independently  



