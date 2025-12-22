# Decision Brain Packaging & Pricing Guide v1.0

## Overview

This guide defines the packaging and pricing structure for Decision Brain services. The approach focuses on **selling diagnosis, not execution** and positioning as a **strategic diagnostic engagement** rather than an AI tool or SaaS product.

## Core Packaging Rules (Non-Negotiable)

✅ **Sell diagnosis, not execution**  
✅ **No subscription pressure at start**  
✅ **No "AI tool" framing**  
✅ **No feature lists**  
✅ **Position as strategic diagnostic engagement**

## Product Structure (3 Tiers Max)

### ✅ TIER 1 — Decision Diagnosis (Entry / Core)

**Name:** Decision Diagnosis

**What it includes:**
- Full Decision Brain analysis (one page / one flow)
- Context-aware outcome detection
- Confidence scoring
- Client-ready decision report
- Clear "what to fix first" logic

**Positioning line:**  
*Identify why users hesitate — before spending on redesign or ads.*

**Pricing logic:**
- High enough to filter unserious clients
- Low enough as entry to larger projects
- Value framing: "One wrong decision can cost more than this diagnosis"

**CTA:** Start with Decision Diagnosis

---

### ✅ TIER 2 — Decision Deep Dive (High-Value Project)

**Name:** Decision Deep Dive

**What it includes:**
- Multi-page or journey-level analysis
- Cross-context outcome comparison
- Secondary outcome modeling
- Strategic decision map
- Priority roadmap (what to change now vs later)

**Positioning line:**  
*Understand how decisions break across the entire user journey.*

**Pricing logic:**
- Project-based pricing
- Value anchored to cost of wrong decisions across multiple touchpoints
- No "per page" language

**CTA:** Start with Decision Diagnosis (upsell happens naturally after diagnosis)

---

### ✅ TIER 3 — Decision Partnership (Advisory)

**Name:** Decision Strategy Partnership

**What it includes:**
- Ongoing decision analysis
- Iterative diagnostics
- Support across launches, pricing, or positioning changes
- Strategic decision advisory

**Positioning line:**  
*A strategic partner focused on how users decide — not just how pages look.*

**Pricing logic:**
- Advisory engagement pricing
- Reflects ongoing strategic value
- Not per-page analysis
- No subscription pressure framing

**CTA:** Start with Decision Diagnosis

---

## Pricing Framing Rules

### ✅ DO:

- Anchor price to cost of wrong decisions
- Use value framing, not hourly logic
- Frame as: "One wrong decision can cost more than this diagnosis"
- Position as strategic investment

### ❌ DON'T:

- Use "per page" language
- Provide ROI guarantees
- Frame as hourly or time-based
- Use SaaS subscription language
- List features without context

## Services Page Requirements

### Structure:

1. **Hero Section**
   - Clear value proposition
   - No feature lists
   - Focus on diagnosis value

2. **Value Proposition**
   - Why decision diagnosis matters
   - Cost of wrong decisions
   - Strategic positioning

3. **Three Packages**
   - Show only the three packages
   - No add-ons
   - No customization menus
   - Each package clearly positioned

4. **CTA Strategy**
   - CTA everywhere → "Start with Decision Diagnosis"
   - All tiers lead to same entry point
   - Upsell happens naturally after diagnosis

### Design Principles:

- Clean, scannable layout
- Premium feel without being pretentious
- No SaaS noise
- No cheap audit vibes
- Professional diagnostic positioning

## Success Criteria

After packaging:

✅ **Clients understand what they're buying in < 60 seconds**  
✅ **Price feels justified by clarity**  
✅ **You control scope**  
✅ **Upsell happens naturally after diagnosis**

## Implementation

### Configuration File

Package definitions are stored in:
- `api/config/pricing_packages.py`

### Services Page

HTML implementation:
- `web/services.html`

### API Integration

Packages can be retrieved programmatically:

```python
from api.config.pricing_packages import get_all_packages, get_package

# Get all packages
packages = get_all_packages()

# Get specific package
diagnosis_package = get_package(PricingTier.DIAGNOSIS)
```

## Pricing Philosophy

### Value-Based Framing

Prices should be framed around:
- **Cost of wrong decisions** (not time spent)
- **Strategic value** (not feature count)
- **Diagnostic clarity** (not execution)

### Entry Strategy

- Tier 1 is the entry point for all clients
- No pressure to start with higher tiers
- Natural upsell after diagnosis reveals deeper needs

### Scope Control

- Clear boundaries for each tier
- No "customization" menus that create scope creep
- Package structure prevents feature creep

## Language Guidelines

### ✅ Use:

- "Decision diagnosis"
- "Strategic diagnostic engagement"
- "Understand why users hesitate"
- "Cost of wrong decisions"
- "What to fix first"

### ❌ Avoid:

- "AI tool"
- "SaaS platform"
- "Per page analysis"
- "ROI guarantee"
- "Feature list"
- "Subscription"
- "Monthly plan"

## Next Steps

1. **Set Actual Prices**: Replace pricing notes with actual values (following the logic, not hardcoding)
2. **Payment Integration**: Connect CTAs to payment/booking flow
3. **Analytics**: Track which tier clients start with and how upsell happens
4. **Refinement**: Iterate based on client feedback and conversion data

## Notes

- All packages lead to the same entry point (Decision Diagnosis)
- Upsell is natural, not forced
- Pricing logic is configurable, not hardcoded
- Focus remains on diagnosis value, not execution





















