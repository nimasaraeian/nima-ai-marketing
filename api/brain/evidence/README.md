# Decision Brain Evidence Modules

This package extends the Decision Brain with Ad and Pricing evidence extraction while preserving the existing landing page analysis logic.

## Architecture

### Core Components

1. **DecisionSignals** (`api/brain/decision_signals.py`)
   - Unified signal structure for all evidence sources
   - Fields: `promise_strength`, `emotional_tone`, `reassurance_level`, `risk_exposure`, `cognitive_load`, `pressure_level`

2. **Evidence Extractors**
   - `landing_signals.py`: Extracts signals from existing PageFeatures
   - `ad_signals.py`: Extracts signals from ad/banner content
   - `pricing_signals.py`: Extracts signals from pricing pages

3. **Signal Merger** (`signal_merger.py`)
   - Merges signals from multiple sources
   - Landing signals: 60% weight (baseline, highest trust)
   - Ad signals: 20% weight (adjustment)
   - Pricing signals: 20% weight (adjustment)

4. **Integration** (`integration.py`)
   - Wraps evidence extraction for easy integration
   - Enriches decision output with evidence metadata

## Usage

### Basic Usage (Landing Only)

```python
from api.brain.evidence.landing_signals import extract_landing_signals
from api.schemas.page_features import PageFeatures

# Extract landing signals from existing PageFeatures
features = PageFeatures(...)  # Your existing features
landing_signals = extract_landing_signals(features)
```

### With Ad Evidence

```python
from api.brain.evidence.ad_signals import extract_ad_signals, AdInput
from api.brain.evidence.signal_merger import merge_signals

# Extract ad signals
ad_input = AdInput(
    ad_copy="Get 50% more leads in 30 days. Guaranteed!",
    ad_headline="Boost Your Sales Today"
)
ad_signals = extract_ad_signals(ad_input)

# Merge with landing signals
merged_signals, confidence = merge_signals(
    landing_signals=landing_signals,
    ad_signals=ad_signals
)
```

### With Pricing Evidence

```python
from api.brain.evidence.pricing_signals import extract_pricing_signals

# Extract pricing signals
pricing_signals = extract_pricing_signals(
    html=pricing_page_html,
    text=pricing_page_text
)

# Merge all signals
merged_signals, confidence = merge_signals(
    landing_signals=landing_signals,
    ad_signals=ad_signals,
    pricing_signals=pricing_signals
)
```

### Full Integration

```python
from api.brain.evidence.integration import EvidenceContext, extract_all_evidence, enrich_decision_output

# Create evidence context
context = EvidenceContext(
    landing_features=page_features,
    ad_input=AdInput(ad_copy="...", ad_headline="..."),
    pricing_html=pricing_html,
    pricing_text=pricing_text
)

# Extract all evidence
evidence_result = extract_all_evidence(context)

# Enrich decision output
enriched_output = enrich_decision_output(
    decision_output=original_decision_output,
    evidence_result=evidence_result
)
```

## Signal Mapping

### Landing → DecisionSignals
- `trustScore` → `reassurance_level`
- `frictionScore` → `cognitive_load` (inverse)
- `clarityScore` → `promise_strength`
- Trust signals (guarantee, security, testimonials) → `risk_exposure`

### Ad → DecisionSignals
- Promise strength analysis → `promise_strength`
- Emotional tone analysis → `emotional_tone`
- Pressure/urgency analysis → `pressure_level`
- Reassurance analysis → `reassurance_level`
- Expectation gap analysis → `expectation_gap`

### Pricing → DecisionSignals
- Choice overload → `cognitive_load`
- Transparency level → `reassurance_level`
- Risk exposure → `risk_exposure`
- Commitment pressure → `pressure_level`

## Output Structure

The enriched decision output includes an `evidence` section:

```json
{
  "decision_blocker": "Outcome Unclear",
  "why": "...",
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

## Constraints

- ✅ **Preserves existing logic**: Landing page analysis unchanged
- ✅ **Additive only**: New modules don't modify existing code
- ✅ **No UI logic**: Pure decision psychology signals
- ✅ **No visual scoring**: Focus on psychological signals only
- ✅ **No CRO checklists**: Decision signals only

## Testing

Run tests with:

```bash
pytest tests/test_evidence_modules.py -v
```



