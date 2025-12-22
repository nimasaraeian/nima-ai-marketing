"""
Human Report Generator from SignalReportV1 (Phase 1 signals)
Generates markdown report from SignalReportV1 (English, no scores).
"""
from typing import Dict, Any, List
from api.schemas.signal_v1 import SignalReportV1


def generate_human_report_from_v1(signal_report: SignalReportV1) -> Dict[str, Any]:
    """
    Generate human-readable markdown report from SignalReportV1.
    
    This function converts Phase 1 signals (SignalReportV1) into a human-readable
    markdown report with verdict, blockers, quick wins, etc.
    
    Args:
        signal_report: SignalReportV1 instance from Phase 1 detection
        
    Returns:
        Dictionary with:
        - human_report: markdown string
        - report_meta: {blockers: [ids], quick_wins: [strings]}
    """
    report_lines = []
    blockers = []
    quick_wins = []
    
    # A) Verdict (based on primary issues)
    verdict_parts = []
    
    if not signal_report.primary_cta_detected:
        verdict_parts.append("**Primary CTA missing**")
        blockers.append("primary_cta_missing")
        quick_wins.append("Add a clear primary CTA button above the fold")
    elif signal_report.cta_count_total > 3:
        verdict_parts.append("**Too many CTAs competing for attention**")
        blockers.append("cta_competition")
        quick_wins.append("Focus on 1 primary CTA above the fold")
    
    if not signal_report.has_pricing:
        verdict_parts.append("**Pricing information not visible**")
        blockers.append("pricing_visibility")
        quick_wins.append("Add clear pricing information")
    
    if not signal_report.has_testimonials and not signal_report.has_logos:
        verdict_parts.append("**No social proof detected**")
        blockers.append("social_proof_missing")
        quick_wins.append("Add testimonials, reviews, or customer logos")
    
    if not signal_report.hero_headline:
        verdict_parts.append("**Hero headline missing or unclear**")
        blockers.append("hero_headline_missing")
        quick_wins.append("Add a clear value proposition headline in hero section")
    
    if verdict_parts:
        verdict = f"The main barrier to conversion is {verdict_parts[0].lower()}."
    else:
        verdict = "The page shows good conversion fundamentals, with minor areas for improvement."
    
    report_lines.append("## Verdict")
    report_lines.append("")
    report_lines.append(verdict)
    report_lines.append("")
    
    # B) Top Blockers (up to 3)
    if blockers:
        report_lines.append("## Top Blockers")
        report_lines.append("")
        
        for i, blocker_id in enumerate(blockers[:3]):
            if blocker_id == "primary_cta_missing":
                report_lines.append("- **Primary CTA Missing** - No clear primary call-to-action detected")
            elif blocker_id == "cta_competition":
                report_lines.append(f"- **CTA Competition** - {signal_report.cta_count_total} CTAs detected, creating confusion")
            elif blocker_id == "pricing_visibility":
                report_lines.append("- **Pricing Visibility** - Pricing information not clearly visible")
            elif blocker_id == "social_proof_missing":
                report_lines.append("- **Social Proof Missing** - No testimonials, reviews, or customer logos detected")
            elif blocker_id == "hero_headline_missing":
                report_lines.append("- **Hero Headline Missing** - No clear headline in hero section")
            else:
                report_lines.append(f"- **{blocker_id.replace('_', ' ').title()}** - Issue detected")
        
        report_lines.append("")
    
    # C) Why Users Hesitate
    report_lines.append("## Why Users Hesitate")
    report_lines.append("")
    
    hesitate_reasons = []
    if not signal_report.primary_cta_detected:
        hesitate_reasons.append("users don't know what action to take")
    if signal_report.cta_count_total > 3:
        hesitate_reasons.append("too many options create decision paralysis")
    if not signal_report.has_pricing:
        hesitate_reasons.append("pricing is unclear, creating uncertainty")
    if not signal_report.has_testimonials and not signal_report.has_logos:
        hesitate_reasons.append("lack of social proof reduces trust")
    if not signal_report.hero_headline:
        hesitate_reasons.append("value proposition is unclear")
    
    if hesitate_reasons:
        hesitate_text = f"Users hesitate because {hesitate_reasons[0]}."
        if len(hesitate_reasons) > 1:
            hesitate_text += f" Additionally, {hesitate_reasons[1]}."
        hesitate_text += " These issues create friction that prevents users from taking action."
    else:
        hesitate_text = "The page shows good fundamentals, but minor improvements could further reduce hesitation."
    
    report_lines.append(hesitate_text)
    report_lines.append("")
    
    # D) Quick Wins
    if quick_wins:
        report_lines.append("## Quick Wins")
        report_lines.append("")
        for i, win in enumerate(quick_wins[:5], 1):
            report_lines.append(f"{i}. {win}")
        report_lines.append("")
    
    # E) Suggested Rewrites
    report_lines.append("## Suggested Rewrites")
    report_lines.append("")
    
    has_suggestions = False
    
    # Headline suggestion
    if not signal_report.hero_headline:
        report_lines.append("**Headline:**")
        report_lines.append("")
        report_lines.append("Current: No clear headline detected")
        report_lines.append("")
        report_lines.append("**Suggested:** Add a clear value proposition headline that states:")
        report_lines.append("- Who you help")
        report_lines.append("- What outcome you deliver")
        report_lines.append("- What problem you solve")
        report_lines.append("")
        report_lines.append("**Example:** \"[Tool] helps [audience] [outcome] by [problem solved]\"")
        report_lines.append("")
        has_suggestions = True
    
    # CTA suggestion
    if not signal_report.primary_cta_detected or signal_report.cta_count_total > 3:
        report_lines.append("**CTA:**")
        report_lines.append("")
        if signal_report.cta_count_total > 3:
            report_lines.append("**Current issue:** Too many CTAs competing for attention")
        else:
            report_lines.append("**Current issue:** No clear primary CTA detected")
        report_lines.append("")
        report_lines.append("**Suggested:** Focus on 1 primary CTA above the fold")
        report_lines.append("")
        has_suggestions = True
    
    if not has_suggestions:
        report_lines.append("No rewrite suggestions - current copy is effective.")
        report_lines.append("")
    
    # F) Checklist
    report_lines.append("## Checklist")
    report_lines.append("")
    
    for action in quick_wins[:5]:
        report_lines.append(f"- [ ] {action}")
    
    report_lines.append("")
    
    # Join all lines
    human_report = "\n".join(report_lines)
    
    return {
        "human_report": human_report,
        "report_meta": {
            "blockers": blockers[:3],
            "quick_wins": quick_wins[:5]
        }
    }

