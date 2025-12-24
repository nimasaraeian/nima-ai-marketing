from typing import List, Dict, Any
from api.schemas.human_report_v1 import HumanReportV1, HumanQuickWin
from api.schemas.signal_v1 import SignalReportV1
from api.schemas.decision_v1 import DecisionLogicV1


# LEGACY_MODE_ENABLED = False  # DISABLED - use human_report_v2 pipeline instead
LEGACY_MODE_ENABLED = False

def render_verdict(decision: DecisionLogicV1) -> str:
    """
    LEGACY FUNCTION - DISABLED by default.
    Use human_report_v2 pipeline instead.
    """
    if not LEGACY_MODE_ENABLED:
        return ""  # Legacy generator disabled
    if not decision.blockers:
        return "No major blockers detected. Conversion potential looks solid."
    
    # top blocker = highest severity then confidence
    sorted_b = sorted(decision.blockers, key=lambda b: (b.severity != "high", -b.confidence))
    top = sorted_b[0].id
    
    if top == "missing_pricing":
        return "The primary decision blocker is missing pricing clarity."
    if top == "weak_trust_signals":
        return "The primary decision blocker is low trust reinforcement (missing proof/assurance signals)."
    if top == "cta_not_detected":
        return "The primary decision blocker is a missing or unclear primary call-to-action."
    if top == "cta_below_fold":
        return "The primary decision blocker is a call-to-action placed below the fold."
    if top == "missing_hero_headline":
        return "The primary decision blocker is a missing or unclear hero headline."
    
    return f"The primary decision blocker is {top}."


def visual_counts_from_elements(signals: SignalReportV1) -> Dict[str, Any]:
    elems = (((signals.raw or {}).get("visual") or {}).get("elements")) if isinstance(signals.raw, dict) else None
    if not elems:
        return {"elements_count": 0}
    
    roles = {}
    for e in elems:
        r = (e.get("role") or "other")
        roles[r] = roles.get(r, 0) + 1
    
    return {
        "elements_count": len(elems),
        "roles": roles
    }


def quickwins_for_blockers(decision: DecisionLogicV1) -> List[HumanQuickWin]:
    wins: List[HumanQuickWin] = []
    ids = {b.id for b in decision.blockers}
    
    if "missing_pricing" in ids:
        wins.append(HumanQuickWin(
            title="Add a pricing anchor (or a 'See pricing' path) above the fold",
            why="Without a price anchor, users can't judge fit quickly and postpone the decision.",
            how=[
                "Add a simple starting price (e.g., 'From $X') or 2-tier range.",
                "If pricing is custom, add a 'Typical range' + 'Get a quote' button.",
                "Place it within the hero section near the primary CTA."
            ],
            impact="high", effort="medium", related_blockers=["missing_pricing"]
        ))
    
    if "weak_trust_signals" in ids:
        wins.append(HumanQuickWin(
            title="Add 1–2 trust reinforcements near the CTA",
            why="A CTA without proof increases perceived risk and reduces conversion confidence.",
            how=[
                "Add 1 short testimonial with a concrete outcome.",
                "Add a small 'worked with / featured in' strip if applicable.",
                "Add a guarantee-style line (e.g., 'No commitment, cancel anytime' if true)."
            ],
            impact="high", effort="low", related_blockers=["weak_trust_signals"]
        ))
    
    if "cta_not_detected" in ids or "cta_below_fold" in ids:
        wins.append(HumanQuickWin(
            title="Make the primary CTA explicit and visually dominant",
            why="If the system struggles to detect a primary CTA, users likely struggle too.",
            how=[
                "Use one primary verb CTA (e.g., 'Request a Diagnostic').",
                "Ensure it appears above the fold and repeats once mid-page.",
                "Reduce competing links near the hero."
            ],
            impact="high", effort="low", related_blockers=[b for b in ["cta_not_detected", "cta_below_fold"] if b in ids]
        ))
    
    if "missing_hero_headline" in ids:
        wins.append(HumanQuickWin(
            title="Add a clear hero headline that states value proposition",
            why="Without a clear headline, users can't quickly understand what you offer.",
            how=[
                "Write a headline that includes: target audience + outcome + problem solved.",
                "Keep it under 12 words and place it prominently above the fold.",
                "Add a supporting subheadline that expands on the value proposition."
            ],
            impact="medium", effort="low", related_blockers=["missing_hero_headline"]
        ))
    
    return wins[:3]


def build_human_report_v1(signals: SignalReportV1, decision: DecisionLogicV1) -> HumanReportV1:
    verdict = render_verdict(decision)
    
    # Top blockers for display
    top_blockers = [
        {"id": b.id, "severity": b.severity, "confidence": b.confidence, "evidence": b.evidence, "metrics": b.metrics}
        for b in sorted(decision.blockers, key=lambda b: (b.severity != "high", -b.confidence))
    ][:3]
    
    # Evidence strings (grounded in inputs/elements)
    evidence = []
    inp = decision.inputs or {}
    
    # Evidence from decision inputs
    evidence.append(f"Primary CTA above fold: {inp.get('cta_count_above_fold', 0)}")
    evidence.append(f"Pricing detected: {inp.get('has_pricing', False)}")
    trust_count = int(inp.get('has_testimonials', False)) + int(inp.get('has_logos', False)) + int(inp.get('has_guarantee', False))
    evidence.append(f"Trust signals (testimonials/logos/guarantee): {trust_count}")
    
    # Evidence from visual elements
    elems = (((signals.raw or {}).get("visual") or {}).get("elements")) if isinstance(signals.raw, dict) else None
    if elems:
        cta_elements = [e for e in elems if e.get("role") in ["primary_cta", "secondary_cta"]]
        if cta_elements:
            evidence.append(f"Visual CTA elements detected: {len(cta_elements)}")
        logo_elements = [e for e in elems if e.get("role") == "logo"]
        if logo_elements:
            evidence.append(f"Logo elements detected: {len(logo_elements)}")
        trust_badges = [e for e in elems if e.get("role") == "trust_badge"]
        if trust_badges:
            evidence.append(f"Trust badge elements detected: {len(trust_badges)}")
    
    visual_summary = visual_counts_from_elements(signals)
    
    # Generate public_summary (5-6 lines, pitch-ready, fully grounded)
    public_summary = _generate_public_summary(decision, signals, top_blockers)
    
    return HumanReportV1(
        url=decision.url,
        verdict=verdict,
        decision_probability=decision.decision_probability,
        top_blockers=top_blockers,
        quick_wins=quickwins_for_blockers(decision),
        evidence=evidence,
        visual_summary=visual_summary,
        public_summary=public_summary,
        debug={"scores": decision.scores, "weights": decision.weights}
    )


def _generate_public_summary(decision: DecisionLogicV1, signals: SignalReportV1, top_blockers: List[Dict[str, Any]]) -> str:
    """
    Generate a 5-6 line pitch-ready summary, fully grounded in decision inputs.
    """
    lines = []
    
    # Line 1: Verdict
    if top_blockers:
        top_id = top_blockers[0].get("id", "")
        if top_id == "missing_pricing":
            lines.append("Verdict: Pricing clarity is missing, preventing users from judging fit quickly.")
        elif top_id == "weak_trust_signals":
            lines.append("Verdict: Trust reinforcement is weak, reducing conversion confidence.")
        elif top_id == "cta_not_detected":
            lines.append("Verdict: Primary call-to-action is missing or unclear.")
        elif top_id == "cta_below_fold":
            lines.append("Verdict: Primary call-to-action is placed below the fold.")
        elif top_id == "missing_hero_headline":
            lines.append("Verdict: Hero headline is missing or unclear.")
        else:
            lines.append(f"Verdict: Primary blocker is {top_id}.")
    else:
        lines.append("Verdict: No major blockers detected. Conversion potential looks solid.")
    
    # Line 2: Evidence (grounded in inputs)
    inp = decision.inputs or {}
    evidence_parts = []
    if not inp.get("has_pricing", False):
        evidence_parts.append("pricing not detected")
    trust_count = int(inp.get("has_testimonials", False)) + int(inp.get("has_logos", False)) + int(inp.get("has_guarantee", False))
    if trust_count == 0:
        evidence_parts.append("no trust signals")
    cta_above = inp.get("cta_count_above_fold", 0)
    if cta_above == 0 and inp.get("cta_count_action", 0) > 0:
        evidence_parts.append("CTA below fold")
    elif inp.get("cta_count_action", 0) == 0:
        evidence_parts.append("no action CTAs detected")
    
    if evidence_parts:
        lines.append(f"Evidence: {', '.join(evidence_parts)}.")
    else:
        lines.append("Evidence: Core conversion elements are present.")
    
    # Line 3: Decision probability context
    prob = decision.decision_probability
    if prob >= 0.7:
        lines.append("Decision probability: High (70%+). Conversion potential is strong.")
    elif prob >= 0.5:
        lines.append("Decision probability: Moderate (50-70%). Some blockers need attention.")
    else:
        lines.append("Decision probability: Low (<50%). Critical blockers are preventing conversion.")
    
    # Line 4-5: Top actions (from quick wins)
    quick_wins = quickwins_for_blockers(decision)
    if quick_wins:
        top_action = quick_wins[0]
        lines.append(f"Next action: {top_action.title.lower()} (impact: {top_action.impact}, effort: {top_action.effort}).")
        if len(quick_wins) > 1:
            second_action = quick_wins[1]
            lines.append(f"Secondary: {second_action.title.lower()} (impact: {second_action.impact}, effort: {second_action.effort}).")
    
    # Line 6: Visual summary (if available)
    raw_dict = signals.raw if isinstance(signals.raw, dict) else {}
    visual_dict = raw_dict.get("visual") if isinstance(raw_dict, dict) else {}
    elems = visual_dict.get("elements") if isinstance(visual_dict, dict) else []
    if elems and len(elems) > 0:
        cta_count = sum(1 for e in elems if e.get("role") in ("primary_cta", "secondary_cta"))
        logo_count = sum(1 for e in elems if e.get("role") == "logo")
        if cta_count > 0 or logo_count > 0:
            parts = []
            if cta_count > 0:
                parts.append(f"{cta_count} CTA{'s' if cta_count > 1 else ''}")
            if logo_count > 0:
                parts.append(f"{logo_count} logo{'s' if logo_count > 1 else ''}")
            if parts:
                lines.append(f"Visual: Detected {', '.join(parts)} above the fold.")
    
    # Join lines (max 6 lines)
    return "\n".join(lines[:6])

