"""
Decision Engine Enhancers - Signature Layers Builder

This module enhances the /api/analyze/url-human response with 4 signature layers:
1. Decision Psychology Insight
2. CTA Recommendations (friction-driven)
3. Cost of Inaction
4. Mindset Personas
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def build_signature_layers(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build 4 signature layers from analysis report.
    
    Args:
        report: Analysis output containing verdict, top_blockers, issues, findings, etc.
        
    Returns:
        Dictionary with 4 new layers:
        - decision_psychology_insight
        - cta_recommendations
        - cost_of_inaction
        - mindset_personas
    """
    # Extract signals from report
    findings = report.get("findings", {})
    top_issues = findings.get("top_issues", [])
    issues_list = findings.get("issues", [])
    
    # Extract issue types and signals
    issue_types = [issue.get("type", "").lower() if isinstance(issue, dict) else str(issue).lower() for issue in top_issues[:3]]
    issue_texts = " ".join([str(issue.get("description", "")) if isinstance(issue, dict) else str(issue) for issue in top_issues[:3]]).lower()
    
    # Detect key signals
    has_trust_issue = any("trust" in it or "social proof" in it or "testimonial" in it or "credibility" in it for it in issue_types) or \
                     "trust" in issue_texts or "social proof" in issue_texts or "testimonial" in issue_texts
    has_pricing_issue = any("pricing" in it or "price" in it or "cost" in it or "effort" in it for it in issue_types) or \
                       "pricing" in issue_texts or "price" in issue_texts or "cost" in issue_texts
    has_cta_competition = any("cta" in it or "button" in it or "choice" in it or "multiple" in it for it in issue_types) or \
                         "multiple cta" in issue_texts or "too many choices" in issue_texts or "cta competition" in issue_texts
    has_clarity_issue = any("unclear" in it or "confusing" in it or "vague" in it or "h1" in it for it in issue_types) or \
                       "unclear" in issue_texts or "confusing" in issue_texts or "vague" in issue_texts
    
    # Get H1 and CTA suggestions from report
    h1_suggestion = None
    primary_cta_suggestion = None
    
    # Try to extract from human_report or findings
    human_report = report.get("human_report", "")
    if human_report:
        # Look for H1 suggestion in report
        if "H1" in human_report or "h1" in human_report:
            lines = human_report.split("\n")
            for i, line in enumerate(lines):
                if "h1" in line.lower() and i + 1 < len(lines):
                    h1_suggestion = lines[i + 1].strip().strip('"').strip("'")
                    break
    
    # Extract CTA suggestions
    quick_wins = findings.get("quick_wins", [])
    for qw in quick_wins[:3]:
        if isinstance(qw, dict):
            qw_text = str(qw.get("description", "")).lower()
            if "cta" in qw_text or "button" in qw_text:
                primary_cta_suggestion = qw.get("description", "")
                break
    
    # 1. Decision Psychology Insight
    decision_psychology_insight = _build_psychology_insight(
        has_trust_issue, has_pricing_issue, has_cta_competition, has_clarity_issue
    )
    
    # 2. CTA Recommendations
    cta_recommendations = _build_cta_recommendations(
        has_trust_issue, has_pricing_issue, has_cta_competition, has_clarity_issue,
        primary_cta_suggestion, report
    )
    
    # 3. Cost of Inaction
    cost_of_inaction = _build_cost_of_inaction(has_trust_issue, has_pricing_issue, has_cta_competition)
    
    # 4. Mindset Personas
    mindset_personas = _build_mindset_personas(
        has_trust_issue, has_pricing_issue, has_cta_competition, has_clarity_issue
    )
    
    return {
        "decision_psychology_insight": decision_psychology_insight,
        "cta_recommendations": cta_recommendations,
        "cost_of_inaction": cost_of_inaction,
        "mindset_personas": mindset_personas
    }


def _build_psychology_insight(
    has_trust: bool, has_pricing: bool, has_cta_comp: bool, has_clarity: bool
) -> Dict[str, str]:
    """Build decision psychology insight based on detected issues."""
    
    if has_trust:
        return {
            "headline": "Competent but Not Yet Safe",
            "insight": "Users see capability but lack the safety signals needed to commit. The page demonstrates competence without building the trust foundation that reduces perceived risk.",
            "why_now": "Trust debt accumulates silently. Each visit without trust signals increases skepticism, making future conversion harder.",
            "micro_risk_reducer": "Add one visible trust signal above the fold: a testimonial, client logo, or guarantee. Small proof beats big promises."
        }
    elif has_pricing:
        return {
            "headline": "Unclear Cost Triggers Delay",
            "insight": "When effort or cost is ambiguous, the mind defaults to assuming the worst-case scenario. This triggers a delay reflex even when the actual cost is reasonable.",
            "why_now": "Pricing ambiguity creates decision paralysis. Users will leave to research elsewhere rather than guess at commitment level.",
            "micro_risk_reducer": "Make cost or effort explicit early. Even if high, clarity reduces anxiety more than mystery."
        }
    elif has_cta_comp:
        return {
            "headline": "Too Many Choices Cause Paralysis",
            "insight": "Multiple CTAs or unclear decision paths create cognitive overload. The brain defaults to inaction when the optimal path is unclear.",
            "why_now": "Choice paralysis increases with each additional option. Users will default to leaving rather than risk choosing wrong.",
            "micro_risk_reducer": "Reduce to one primary CTA above the fold. Secondary actions can exist, but make the primary path unmistakable."
        }
    elif has_clarity:
        return {
            "headline": "Unclear Value Blocks Decision",
            "insight": "When the core value proposition is ambiguous, users cannot form a clear mental model of what they're deciding about. This blocks all decision pathways.",
            "why_now": "Clarity is the foundation of all decisions. Without it, trust, pricing, and CTA optimization cannot help.",
            "micro_risk_reducer": "Clarify the H1 and hero section. State what this is, who it's for, and what happens next in one clear sentence."
        }
    else:
        # Default insight
        return {
            "headline": "Decision Friction Detected",
            "insight": "Multiple subtle friction points are creating hesitation. Users are close to deciding but need one clear path forward.",
            "why_now": "Small frictions compound. Addressing the primary blocker unlocks the decision pathway.",
            "micro_risk_reducer": "Focus on the top blocker identified in the analysis. One clear fix will unlock the decision."
        }


def _build_cta_recommendations(
    has_trust: bool, has_pricing: bool, has_cta_comp: bool, has_clarity: bool,
    existing_cta: str, report: Dict[str, Any]
) -> Dict[str, Any]:
    """Build friction-driven CTA recommendations."""
    
    # Determine if strongly transactional
    page_type = report.get("page_type", "").lower()
    goal = report.get("summary", {}).get("goal", "").lower()
    is_transactional = "buy" in goal or "purchase" in goal or "checkout" in page_type or "pricing" in page_type
    
    # Primary CTA
    if has_trust:
        primary = {
            "label": "See Why Users Hesitate",
            "reason": "Addresses trust concerns by showing you understand hesitation patterns"
        }
    elif has_pricing:
        primary = {
            "label": "Get Clear Pricing",
            "reason": "Reduces pricing ambiguity that triggers delay"
        }
    elif has_cta_comp:
        primary = {
            "label": "Reduce Decision Friction",
            "reason": "Directly addresses choice paralysis from multiple CTAs"
        }
    elif has_clarity:
        primary = {
            "label": "Get a Conversion Diagnosis",
            "reason": "Helps clarify value proposition and decision path"
        }
    else:
        primary = {
            "label": "See Why Users Hesitate" if not is_transactional else "Get Started",
            "reason": "Focuses on understanding decision friction" if not is_transactional else "Direct action for transactional pages"
        }
    
    # Secondary CTAs (up to 2)
    secondary = []
    if has_trust and not has_pricing:
        secondary.append({
            "label": "View Case Studies",
            "reason": "Builds trust through proof without adding pricing pressure"
        })
    if has_clarity:
        secondary.append({
            "label": "Understand Your Options",
            "reason": "Helps clarify value and reduce confusion"
        })
    if len(secondary) == 0:
        secondary.append({
            "label": "Learn More",
            "reason": "Low-pressure option for users not ready to commit"
        })
    
    # Do not use CTAs (up to 2)
    do_not_use = []
    if has_cta_comp:
        do_not_use.append({
            "label": "Get Started",
            "reason": "Too generic when multiple CTAs already exist, adds to choice paralysis"
        })
    if has_trust and not is_transactional:
        do_not_use.append({
            "label": "Buy Now",
            "reason": "High-pressure CTA increases risk perception when trust is low"
        })
    if len(do_not_use) == 0:
        do_not_use.append({
            "label": "Click Here",
            "reason": "Generic and provides no value signal or friction reduction"
        })
    
    return {
        "primary": primary,
        "secondary": secondary[:2],  # Max 2
        "do_not_use": do_not_use[:2]  # Max 2
    }


def _build_cost_of_inaction(
    has_trust: bool, has_pricing: bool, has_cta_comp: bool
) -> Dict[str, Any]:
    """Build cost of inaction impact box."""
    
    bullets = []
    
    if has_trust:
        bullets.append("Lower conversion rates as visitors leave without trust signals")
        bullets.append("Wasted traffic from users who would convert with proper proof")
    elif has_pricing:
        bullets.append("Delayed decisions as users research pricing elsewhere")
        bullets.append("Lost opportunities from pricing ambiguity causing abandonment")
    elif has_cta_comp:
        bullets.append("Choice paralysis reducing overall conversion")
        bullets.append("Lower lead quality from unclear decision paths")
    else:
        bullets.append("Lower conversion rates from unresolved friction")
        bullets.append("Wasted traffic from unclear value proposition")
        bullets.append("Delayed trust building from missing signals")
    
    # Ensure exactly 3 bullets
    while len(bullets) < 3:
        bullets.append("Reduced ROI from suboptimal conversion funnel")
    bullets = bullets[:3]
    
    metric_hint = "Track conversion rate, time-to-convert, and bounce rate to measure impact"
    
    return {
        "headline": "What This Is Costing You",
        "bullets": bullets,
        "metric_hint": metric_hint
    }


def _build_mindset_personas(
    has_trust: bool, has_pricing: bool, has_cta_comp: bool, has_clarity: bool
) -> List[Dict[str, str]]:
    """Build 3 mindset personas with tailored CTAs and next steps."""
    
    # Hesitant Visitor
    if has_trust:
        hesitant = {
            "id": "hesitant",
            "title": "Hesitant Visitor",
            "signal": "Trust/risk dominant - sees capability but lacks safety signals",
            "goal": "Reduce perceived risk before committing",
            "best_cta": "See Why Users Hesitate",
            "next_step": "Add trust signals (testimonials, guarantees, client logos) above the fold"
        }
    elif has_pricing:
        hesitant = {
            "id": "hesitant",
            "title": "Hesitant Visitor",
            "signal": "Pricing/effort uncertainty triggers delay reflex",
            "goal": "Clarify cost or effort to reduce anxiety",
            "best_cta": "Get Clear Pricing",
            "next_step": "Make pricing or effort explicit early, even if high"
        }
    else:
        hesitant = {
            "id": "hesitant",
            "title": "Hesitant Visitor",
            "signal": "Risk perception outweighs reward signals",
            "goal": "Build safety and reduce perceived risk",
            "best_cta": "See Why Users Hesitate",
            "next_step": "Add risk reversal mechanisms (guarantees, low-commitment options)"
        }
    
    # Curious Evaluator
    if has_clarity:
        curious = {
            "id": "curious",
            "title": "Curious Evaluator",
            "signal": "Clarity/value dominant - needs to understand before deciding",
            "goal": "Understand value proposition and fit",
            "best_cta": "Get a Conversion Diagnosis",
            "next_step": "Clarify H1 and hero section with clear value statement"
        }
    elif has_pricing:
        curious = {
            "id": "curious",
            "title": "Curious Evaluator",
            "signal": "Needs pricing clarity to evaluate fit",
            "goal": "Understand cost and commitment level",
            "best_cta": "Get Clear Pricing",
            "next_step": "Make pricing structure transparent and easy to understand"
        }
    else:
        curious = {
            "id": "curious",
            "title": "Curious Evaluator",
            "signal": "Clarity/value dominant - evaluating fit and value",
            "goal": "Understand what this is and if it's for them",
            "best_cta": "Understand Your Options",
            "next_step": "Improve value proposition clarity in hero section"
        }
    
    # Ready-to-Act Buyer
    if has_cta_comp:
        ready = {
            "id": "ready",
            "title": "Ready-to-Act Buyer",
            "signal": "CTA/flow/effort dominant - ready but blocked by choice paralysis",
            "goal": "Clear decision path without multiple options",
            "best_cta": "Reduce Decision Friction",
            "next_step": "Simplify to one primary CTA above the fold, remove competing choices"
        }
    elif has_pricing:
        ready = {
            "id": "ready",
            "title": "Ready-to-Act Buyer",
            "signal": "Ready to commit but blocked by pricing ambiguity",
            "goal": "Clear pricing to complete decision",
            "best_cta": "Get Clear Pricing",
            "next_step": "Make pricing visible and clear to remove final blocker"
        }
    else:
        ready = {
            "id": "ready",
            "title": "Ready-to-Act Buyer",
            "signal": "CTA/flow/effort dominant - ready to act but needs clear path",
            "goal": "Clear, friction-free path to action",
            "best_cta": "Get Started",
            "next_step": "Optimize CTA placement and reduce friction in conversion flow"
        }
    
    return [hesitant, curious, ready]

