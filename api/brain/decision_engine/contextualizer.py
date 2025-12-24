"""
Contextualizer - Reframe analysis for enterprise/mature brands

Reframes verdicts, insights, and recommendations to avoid naive verdicts
for well-known enterprise brands like Stripe, Notion, etc.
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Forbidden phrases for enterprise/large brands
FORBIDDEN_TRUST_PHRASES = [
    "untrustworthy",
    "lacks trust signals",
    "feels risky",
    "no trust",
    "missing trust signals",
    "trust signals are missing",
    "feels unsafe",
    "sketchy",
    "unproven",
    "not trustworthy"
]

# Safe replacement phrases
SAFE_REPLACEMENTS = {
    "untrustworthy": "information density increases cognitive load",
    "lacks trust signals": "next-step ambiguity",
    "feels risky": "choice overload / decision paralysis",
    "no trust": "first-time or price-sensitive visitors may hesitate",
    "missing trust signals": "next-step ambiguity",
    "trust signals are missing": "next-step ambiguity",
    "feels unsafe": "decision friction",
    "sketchy": "unclear value proposition",
    "unproven": "needs clarity for first-time visitors",
    "not trustworthy": "information density creates hesitation"
}


def sanitize_text(text: str, ctx: Dict[str, Any]) -> str:
    """
    Sanitize text to remove forbidden trust phrases for enterprise/large brands.
    
    Args:
        text: Text to sanitize
        ctx: Context dict with brand_context and page_type
        
    Returns:
        Sanitized text
    """
    if not text:
        return text
    
    brand_context = ctx.get("brand_context", {})
    page_type = ctx.get("page_type", {})
    
    brand_maturity = brand_context.get("brand_maturity", "startup")
    page_type_name = page_type.get("type", "unknown")
    
    # Apply sanitization if enterprise/growth OR ecommerce
    should_sanitize = (
        brand_maturity in ["enterprise", "growth"] or
        str(page_type_name).startswith("ecommerce_")
    )
    
    if not should_sanitize:
        return text
    
    text_lower = text.lower()
    sanitized = text
    
    # Replace forbidden phrases
    for forbidden, replacement in SAFE_REPLACEMENTS.items():
        if forbidden in text_lower:
            # Case-insensitive replacement
            import re
            pattern = re.compile(re.escape(forbidden), re.IGNORECASE)
            sanitized = pattern.sub(replacement, sanitized)
            logger.debug(f"Sanitized '{forbidden}' -> '{replacement}' in text")
    
    return sanitized


def contextualize_verdict(payload: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Contextualize verdict and recommendations for enterprise brands.
    
    Args:
        payload: Response payload with human_report, decision_psychology_insight, etc.
        ctx: Context dict with brand_context and page_intent
        
    Returns:
        Modified payload with contextualized text fields
    """
    brand_context = ctx.get("brand_context", {})
    page_intent = ctx.get("page_intent", {})
    
    analysis_mode = brand_context.get("analysis_mode", "standard")
    
    # Only contextualize if enterprise_context_aware mode
    if analysis_mode != "enterprise_context_aware":
        return payload
    
    intent = page_intent.get("intent", "unknown")
    
    # Add context note
    payload["context_note"] = {
        "headline": "Context Note",
        "text": "This page appears optimized for informed users. Findings below may mainly affect first-time or price-sensitive visitors."
    }
    
    # Apply hard guards: sanitize all text fields
    # Contextualize human_report/verdict
    if "human_report" in payload:
        human_report = payload["human_report"]
        # Always sanitize first
        human_report = sanitize_text(human_report, ctx)
        if intent == "pricing":
            # Reframe pricing page verdicts (always reframe for pricing pages in enterprise mode)
            human_report = _reframe_pricing_verdict(human_report)
        # Sanitize again after reframing
        human_report = sanitize_text(human_report, ctx)
        payload["human_report"] = human_report
    
    # Contextualize decision_psychology_insight
    if "decision_psychology_insight" in payload:
        insight = payload["decision_psychology_insight"]
        if intent == "pricing":
            insight = _reframe_pricing_insight(insight)
        elif intent == "docs":
            insight = _reframe_docs_insight(insight)
        # Sanitize all insight text fields
        for key in ["headline", "insight", "why_now", "micro_risk_reducer"]:
            if key in insight:
                insight[key] = sanitize_text(str(insight[key]), ctx)
        payload["decision_psychology_insight"] = insight
    
    # Contextualize CTA recommendations
    if "cta_recommendations" in payload:
        cta_rec = payload["cta_recommendations"]
        if intent == "pricing":
            cta_rec = _reframe_pricing_ctas(cta_rec)
        else:
            cta_rec = _reframe_enterprise_ctas(cta_rec)
        payload["cta_recommendations"] = cta_rec
    
    # Contextualize mindset personas
    if "mindset_personas" in payload:
        personas = payload["mindset_personas"]
        personas = _reframe_enterprise_personas(personas, intent)
        # Sanitize persona text fields
        for persona in personas:
            for key in ["title", "signal", "goal", "best_cta", "next_step"]:
                if key in persona:
                    persona[key] = sanitize_text(str(persona[key]), ctx)
        payload["mindset_personas"] = personas
    
    return payload


def _reframe_pricing_verdict(verdict: str) -> str:
    """Reframe pricing page verdict to avoid naive trust claims."""
    # Replace trust-related naive claims
    verdict = verdict.replace("trust signals are missing", "next-step ambiguity may increase hesitation")
    verdict = verdict.replace("no trust signals", "next-step ambiguity")
    verdict = verdict.replace("missing trust signals", "next-step ambiguity")
    
    # Add enterprise context if not present
    if "informed buyers" not in verdict.lower() and "first-time" not in verdict.lower():
        # Try to insert context-aware language
        if "## Verdict" in verdict:
            # Insert after Verdict heading
            lines = verdict.split("\n")
            new_lines = []
            for i, line in enumerate(lines):
                new_lines.append(line)
                if line.strip() == "## Verdict" and i + 1 < len(lines):
                    # Add context-aware note after verdict
                    new_lines.append("This pricing page is optimized for informed buyers, but may increase hesitation for first-time or price-sensitive visitors due to next-step ambiguity and information density.")
                    break
            verdict = "\n".join(new_lines)
    
    return verdict


def _reframe_pricing_insight(insight: Dict[str, str]) -> Dict[str, str]:
    """Reframe pricing page psychology insight."""
    # Never claim trust signals missing for enterprise pricing pages
    if "trust" in insight.get("headline", "").lower() or "trust" in insight.get("insight", "").lower():
        insight["headline"] = "Next-Step Ambiguity Triggers Delay"
        insight["insight"] = "This pricing page is optimized for informed buyers, but may increase hesitation for first-time or price-sensitive visitors due to next-step ambiguity and information density."
        insight["why_now"] = "Information density and unclear next steps create decision delay, especially for visitors not yet familiar with the product."
        insight["micro_risk_reducer"] = "Clarify the immediate next step after plan selection. Reduce cognitive load by chunking information."
    
    # Add strategic choice note
    if "strategic_choice" not in insight:
        insight["strategic_choice"] = "Some patterns here may be intentional for brand positioning; the goal is to reduce hesitation for specific visitor mindsets, not to criticize the product."
    
    return insight


def _reframe_docs_insight(insight: Dict[str, str]) -> Dict[str, str]:
    """Reframe docs page insight to focus on clarity/navigation."""
    insight["headline"] = "Navigation and Effort Optimization"
    insight["insight"] = "Documentation pages are optimized for developers who know what they're looking for. Focus on clarity, navigation, and effort reduction rather than CTA optimization."
    insight["why_now"] = "Documentation clarity directly impacts developer experience and product adoption."
    insight["micro_risk_reducer"] = "Improve navigation structure and reduce cognitive effort to find information."
    
    return insight


def _reframe_pricing_ctas(cta_rec: Dict[str, Any]) -> Dict[str, Any]:
    """Reframe CTA recommendations for pricing pages."""
    # Replace generic CTAs with friction-diagnostic ones
    primary = cta_rec.get("primary", {})
    
    # Use friction-diagnostic CTAs
    friction_ctas = [
        {"label": "See Where First-Time Users Hesitate", "reason": "Identifies friction points for new visitors"},
        {"label": "Reduce Decision Friction", "reason": "Addresses choice paralysis and next-step ambiguity"},
        {"label": "Find the Moment Users Pause", "reason": "Pinpoints hesitation triggers in pricing flow"}
    ]
    
    # Replace primary if it's generic
    primary_label = primary.get("label", "").lower()
    generic_ctas = ["get started", "start your journey", "learn more"]
    if any(gen in primary_label for gen in generic_ctas):
        primary = friction_ctas[0]
    else:
        # Keep existing if already friction-focused
        pass
    
    cta_rec["primary"] = primary
    
    # Update secondary for pricing
    secondary = cta_rec.get("secondary", [])
    pricing_secondaries = [
        {"label": "Compare Plans Clearly", "reason": "Reduces cognitive load in plan comparison"},
        {"label": "View Plan Differences", "reason": "Clarifies options and reduces choice paralysis"}
    ]
    if len(secondary) < 2:
        secondary = pricing_secondaries[:2]
    cta_rec["secondary"] = secondary
    
    return cta_rec


def _reframe_enterprise_ctas(cta_rec: Dict[str, Any]) -> Dict[str, Any]:
    """Reframe CTA recommendations for enterprise pages (non-pricing)."""
    primary = cta_rec.get("primary", {})
    primary_label = primary.get("label", "").lower()
    
    # Replace generic CTAs
    generic_ctas = ["get started", "start your journey", "learn more"]
    if any(gen in primary_label for gen in generic_ctas):
        primary = {
            "label": "See Why Users Hesitate",
            "reason": "Addresses decision friction for enterprise buyers"
        }
        cta_rec["primary"] = primary
    
    return cta_rec


def _reframe_enterprise_personas(personas: list, intent: str) -> list:
    """Reframe personas for enterprise context."""
    for persona in personas:
        if persona.get("id") == "hesitant":
            persona["title"] = "First-Time / Non-Expert / Risk-Sensitive Visitor"
            persona["signal"] = "First-time or non-expert visitor who needs more context before deciding"
            if intent == "pricing":
                persona["goal"] = "Understand pricing structure and next steps without feeling overwhelmed"
                persona["best_cta"] = "See Where First-Time Users Hesitate"
                persona["next_step"] = "Simplify pricing presentation and clarify immediate next steps"
        elif persona.get("id") == "ready":
            persona["title"] = "Informed Buyer Needs Clear Next Step"
            persona["signal"] = "Informed buyer ready to act but needs clear next step"
            if intent == "pricing":
                persona["goal"] = "Complete purchase with minimal friction"
                persona["best_cta"] = "Reduce Decision Friction"
                persona["next_step"] = "Optimize checkout flow and reduce cognitive load"
    
    return personas

