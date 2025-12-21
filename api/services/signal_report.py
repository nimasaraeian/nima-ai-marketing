"""
Human Report Generator from Decision Signals
Generates markdown report from 12 decision signals (English, no scores).
"""
import re
from typing import Dict, Any, List, Tuple


def _normalize_encoding_artifacts(text: str) -> str:
    """
    Normalize common encoding artifacts (mojibake) in text.
    Fixes UTF-8 text that was mistakenly decoded as Latin-1/CP1252.
    
    Common fixes:
    - "â€"" or "â€"" -> "—" (em dash)
    - "â€"" -> "\"" (right double quote)
    - "â€œ" -> "\"" (left double quote)
    - "â€™" -> "'" (right single quote)
    - "â€"" -> "–" (en dash)
    """
    if not text:
        return text
    
    # Common mojibake fixes (UTF-8 decoded as cp1252/latin1)
    # These are the actual character sequences that appear when UTF-8 is decoded as Latin-1
    replacements = {
        # Em dash: UTF-8 bytes E2 80 94 decoded as Latin-1
        "\u00e2\u0080\u0094": "—",  # â€" -> —
        "\u00e2\u2014": "—",  # Alternative representation
        # En dash: UTF-8 bytes E2 80 93 decoded as Latin-1
        "\u00e2\u0080\u0093": "–",  # â€" -> –
        # Right double quote: UTF-8 bytes E2 80 9D decoded as Latin-1
        "\u00e2\u0080\u009d": "\"",  # â€" -> "
        # Left double quote: UTF-8 bytes E2 80 9C decoded as Latin-1
        "\u00e2\u0080\u009c": "\"",  # â€œ -> "
        # Right single quote: UTF-8 bytes E2 80 99 decoded as Latin-1
        "\u00e2\u0080\u0099": "'",  # â€™ -> '
        # Left single quote: UTF-8 bytes E2 80 98 decoded as Latin-1
        "\u00e2\u0080\u0098": "'",  # â€˜ -> '
        # Ellipsis: UTF-8 bytes E2 80 A6 decoded as Latin-1
        "\u00e2\u0080\u00a6": "…",  # â€¦ -> …
        # Bullet: UTF-8 bytes E2 80 A2 decoded as Latin-1
        "\u00e2\u0080\u00a2": "•",  # â€¢ -> •
        # Common single character artifacts
        "\u00c3": "",  # Ã (common artifact)
        "\u00e2": "",  # â (if standalone)
    }
    
    # Apply replacements in order (longer patterns first)
    normalized = text
    for broken, fixed in sorted(replacements.items(), key=lambda x: len(x[0]), reverse=True):
        normalized = normalized.replace(broken, fixed)
    
    # Also handle regex patterns for common mojibake sequences
    # These patterns match the actual broken character sequences as they appear
    # Em dash: â€" or â€" (various representations)
    normalized = re.sub(r'â€[""]', '—', normalized)
    normalized = re.sub(r'â€[""]', '—', normalized)
    # En dash: â€"
    normalized = re.sub(r'â€[""]', '–', normalized)
    # Right double quote: â€"
    normalized = re.sub(r'â€[""]', '"', normalized)
    # Left double quote: â€œ
    normalized = re.sub(r'â€œ', '"', normalized)
    # Right single quote: â€™
    normalized = re.sub(r'â€™', "'", normalized)
    # Left single quote: â€˜
    normalized = re.sub(r'â€˜', "'", normalized)
    # Ellipsis: â€¦
    normalized = re.sub(r'â€¦', '…', normalized)
    # Bullet: â€¢
    normalized = re.sub(r'â€¢', '•', normalized)
    
    # Handle standalone "â" (U+00E2) that might be a corrupted em dash or other character
    # This is a common artifact when em dash "—" (U+2014) gets corrupted to just "â" (U+00E2)
    # Pattern: "Label â Text" should become "Label - Text"
    # Simple direct replacement: replace all instances of "â" with " - "
    # Use both Unicode escape and literal character for maximum compatibility
    normalized = normalized.replace('\u00e2', ' - ')
    normalized = normalized.replace('â', ' - ')
    # Clean up any triple spaces or more that might have been created
    normalized = re.sub(r' {3,}', ' ', normalized)
    # Clean up double spaces (but preserve intentional spacing)
    normalized = re.sub(r'([^\s])\s{2,}([^\s])', r'\1 - \2', normalized)
    
    return normalized


# Severity weights for ranking blockers
SEVERITY_WEIGHTS = {
    "missing": 3,
    "weak": 2,
    "unclear": 1,
    "present": 0
}

# Safe generic templates for fallback
SAFE_TEMPLATE = {
    "reason_line": "Insufficient evidence to confirm, but this area may be affecting decisions.",
    "action_line": "Add/adjust this element and retest."
}

# All 12 signal IDs
ALL_SIGNAL_IDS = [
    "value_prop_presence",
    "value_prop_specificity",
    "information_hierarchy",
    "primary_cta_presence",
    "cta_clarity",
    "cta_competition",
    "social_proof_presence",
    "risk_reducers",
    "legitimacy_signals",
    "pricing_visibility",
    "form_friction",
    "cognitive_load"
]

# All statuses that need templates
ALL_STATUSES = ["missing", "weak", "unclear"]


# Templates for signal.id + status combinations (36 templates total)
SIGNAL_TEMPLATES = {
    # Value Proposition Presence
    ("value_prop_presence", "missing"): {
        "reason_line": "No clear value proposition in hero section",
        "action_line": "Add clear value proposition: who you help, what outcome, what problem solved"
    },
    ("value_prop_presence", "weak"): {
        "reason_line": "Value proposition is too generic",
        "action_line": "Make value proposition specific: who it helps, what outcome, what problem solved"
    },
    ("value_prop_presence", "unclear"): {
        "reason_line": "Insufficient evidence to confirm value proposition clarity",
        "action_line": "Review and clarify value proposition, then retest"
    },
    # Value Proposition Specificity
    ("value_prop_specificity", "missing"): {
        "reason_line": "Value proposition uses vague language without specifics",
        "action_line": "Replace vague claims with specific numbers, results, and concrete details"
    },
    ("value_prop_specificity", "weak"): {
        "reason_line": "Value proposition mixes specific and vague language",
        "action_line": "Replace remaining vague terms with specific numbers and results"
    },
    ("value_prop_specificity", "unclear"): {
        "reason_line": "Insufficient evidence to assess value proposition specificity",
        "action_line": "Review value proposition for specific details, then retest"
    },
    # Information Hierarchy
    ("information_hierarchy", "missing"): {
        "reason_line": "No clear H1 or CTA - users don't know what to read first",
        "action_line": "Add H1 headline and clear CTA to establish information hierarchy"
    },
    ("information_hierarchy", "weak"): {
        "reason_line": "Incomplete hierarchy - users may not know what to read first",
        "action_line": "Ensure clear hierarchy: H1 → supporting text → CTA"
    },
    ("information_hierarchy", "unclear"): {
        "reason_line": "Insufficient evidence to confirm information hierarchy",
        "action_line": "Review page structure and hierarchy, then retest"
    },
    # Primary CTA Presence
    ("primary_cta_presence", "missing"): {
        "reason_line": "No action-oriented CTA detected",
        "action_line": "Add clear primary CTA with action verbs (start, get, try, request, book)"
    },
    ("primary_cta_presence", "weak"): {
        "reason_line": "CTA keywords found but no clear CTA button",
        "action_line": "Add prominent action-oriented CTA button (e.g., 'Get Started', 'Try Now')"
    },
    ("primary_cta_presence", "unclear"): {
        "reason_line": "Insufficient evidence to confirm primary CTA presence",
        "action_line": "Review and add primary CTA if missing, then retest"
    },
    # CTA Clarity
    ("cta_clarity", "missing"): {
        "reason_line": "CTAs are vague and don't state the outcome",
        "action_line": "Replace vague CTAs with outcome-focused ones (e.g., 'Get Report', 'Start Analysis')"
    },
    ("cta_clarity", "weak"): {
        "reason_line": "Some CTAs are vague (e.g., 'Submit', 'Click Here')",
        "action_line": "Make all CTAs outcome-focused (e.g., 'Get Report' not 'Submit')"
    },
    ("cta_clarity", "unclear"): {
        "reason_line": "Insufficient evidence to assess CTA clarity",
        "action_line": "Review CTA text for clarity and outcome focus, then retest"
    },
    # CTA Competition
    ("cta_competition", "missing"): {
        "reason_line": "Too many CTAs - high competition, unclear focus",
        "action_line": "Focus on 1 primary action - too many CTAs confuse users"
    },
    ("cta_competition", "weak"): {
        "reason_line": "Multiple CTAs in hero - moderate competition",
        "action_line": "Consider reducing to 1 primary CTA for better focus"
    },
    ("cta_competition", "unclear"): {
        "reason_line": "Insufficient evidence to assess CTA competition",
        "action_line": "Review CTA count and placement, then retest"
    },
    # Social Proof Presence
    ("social_proof_presence", "missing"): {
        "reason_line": "No social proof detected",
        "action_line": "Add testimonials, reviews, customer logos, or 'trusted by' section"
    },
    ("social_proof_presence", "weak"): {
        "reason_line": "Limited social proof indicators",
        "action_line": "Add testimonials, reviews, customer logos, or 'trusted by' section"
    },
    ("social_proof_presence", "unclear"): {
        "reason_line": "Insufficient evidence to confirm social proof presence",
        "action_line": "Review and add social proof elements if missing, then retest"
    },
    # Risk Reducers
    ("risk_reducers", "missing"): {
        "reason_line": "No risk reduction signals detected",
        "action_line": "Add free trial, money-back guarantee, or 'cancel anytime' messaging"
    },
    ("risk_reducers", "weak"): {
        "reason_line": "Limited risk reduction signals",
        "action_line": "Add free trial, money-back guarantee, or 'cancel anytime' messaging"
    },
    ("risk_reducers", "unclear"): {
        "reason_line": "Insufficient evidence to confirm risk reduction signals",
        "action_line": "Review and add risk reduction messaging if missing, then retest"
    },
    # Legitimacy Signals
    ("legitimacy_signals", "missing"): {
        "reason_line": "No legitimacy signals detected (contact, about, privacy, terms)",
        "action_line": "Add contact information, about page, privacy policy, and terms of service"
    },
    ("legitimacy_signals", "weak"): {
        "reason_line": "Limited legitimacy indicators",
        "action_line": "Add contact information, about page, privacy policy, and terms of service"
    },
    ("legitimacy_signals", "unclear"): {
        "reason_line": "Insufficient evidence to confirm legitimacy signals",
        "action_line": "Review and add legitimacy signals if missing, then retest"
    },
    # Pricing Visibility
    ("pricing_visibility", "missing"): {
        "reason_line": "No pricing information detected - unclear pricing path",
        "action_line": "Add clear pricing information to reduce friction"
    },
    ("pricing_visibility", "weak"): {
        "reason_line": "Pricing path may be unclear",
        "action_line": "Make pricing more prominent and clear to reduce friction"
    },
    ("pricing_visibility", "unclear"): {
        "reason_line": "Insufficient evidence to confirm pricing visibility",
        "action_line": "Review pricing visibility and clarity, then retest"
    },
    # Form Friction
    ("form_friction", "missing"): {
        "reason_line": "Complex form or form appears too early before value is communicated",
        "action_line": "Simplify form or move it after value is communicated"
    },
    ("form_friction", "weak"): {
        "reason_line": "Moderate form complexity",
        "action_line": "Keep forms simple and only ask for essential information"
    },
    ("form_friction", "unclear"): {
        "reason_line": "Insufficient evidence to assess form friction",
        "action_line": "Review form complexity and placement, then retest"
    },
    # Cognitive Load
    ("cognitive_load", "missing"): {
        "reason_line": "High cognitive load - too much text, conflicting messages, unclear hierarchy",
        "action_line": "Reduce text, improve hierarchy with clear H1/H2, remove conflicting messages"
    },
    ("cognitive_load", "weak"): {
        "reason_line": "Moderate cognitive load - some organization issues",
        "action_line": "Reduce text, improve hierarchy with clear H1/H2, remove conflicting messages"
    },
    ("cognitive_load", "unclear"): {
        "reason_line": "Insufficient evidence to assess cognitive load",
        "action_line": "Review content organization and hierarchy, then retest"
    },
}


def _get_template(signal_id: str, status: str) -> Tuple[str, str]:
    """
    Get template for signal.id + status.
    Always returns a tuple (reason_line, action_line) - never empty.
    """
    key = (signal_id, status)
    if key in SIGNAL_TEMPLATES:
        template = SIGNAL_TEMPLATES[key]
        return template["reason_line"], template["action_line"]
    
    # Safe fallback - never return empty
    return SAFE_TEMPLATE["reason_line"], SAFE_TEMPLATE["action_line"]


def rank_blockers(signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank blockers by severity.
    
    Rules:
    - Eligible blockers: status in {"missing", "weak"} only
    - If fewer than 3 eligible, fill with highest-rank "unclear" but label as "Potential Issues"
    - Never allow "unclear" to be the #1 blocker
    
    Returns list of blocker dicts with: id, status, rank, is_potential
    """
    eligible_blockers = []
    unclear_blockers = []
    
    for signal in signals:
        status = signal.get("status", "unclear")
        confidence = signal.get("confidence", 0.5)
        signal_id = signal.get("id")
        
        if status in ["missing", "weak"]:
            # Eligible blockers
            severity = SEVERITY_WEIGHTS.get(status, 2)
            rank = severity * (1.0 - confidence + 0.25)
            eligible_blockers.append({
                "id": signal_id,
                "rank": rank,
                "status": status,
                "confidence": confidence,
                "is_potential": False
            })
        elif status == "unclear":
            # Potential issues (low evidence)
            severity = SEVERITY_WEIGHTS.get("unclear", 1)
            rank = severity * (1.0 - confidence + 0.25)
            unclear_blockers.append({
                "id": signal_id,
                "rank": rank,
                "status": status,
                "confidence": confidence,
                "is_potential": True
            })
    
    # Sort by rank (highest first)
    eligible_blockers.sort(key=lambda x: x["rank"], reverse=True)
    unclear_blockers.sort(key=lambda x: x["rank"], reverse=True)
    
    # Take top 3 from eligible
    result = eligible_blockers[:3]
    
    # If fewer than 3 eligible, fill with unclear (but never as #1)
    if len(result) < 3 and len(unclear_blockers) > 0:
        needed = 3 - len(result)
        # Only add unclear if we already have at least 1 eligible (so unclear is never #1)
        if len(result) > 0:
            result.extend(unclear_blockers[:needed])
    
    return result


def generate_human_report(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate human-readable markdown report from decision signals.
    
    Returns:
        {
            "human_report": markdown string,
            "report_meta": {
                "blockers": [signal_ids],
                "quick_wins": [action strings]
            }
        }
    """
    # Rank blockers (returns list of dicts with is_potential flag)
    blocker_list = rank_blockers(signals)
    blocker_ids = [b["id"] for b in blocker_list]
    
    # Get blocker signals
    signal_dict = {s["id"]: s for s in signals}
    blockers = []
    for blocker_info in blocker_list:
        signal_id = blocker_info["id"]
        if signal_id in signal_dict:
            signal = signal_dict[signal_id].copy()
            signal["is_potential"] = blocker_info.get("is_potential", False)
            blockers.append(signal)
    
    # Build report sections
    report_lines = []
    quick_wins = []
    
    # A) Verdict (1 sentence using top blocker)
    if blockers and not blockers[0].get("is_potential", False):
        top_blocker = blockers[0]
        label = top_blocker.get("label", "Issue")
        reason_line, _ = _get_template(top_blocker.get("id"), top_blocker.get("status"))
        reason_line = _normalize_encoding_artifacts(reason_line)
        
        verdict = f"The main barrier to conversion is **{label}**: {reason_line.lower()}."
    elif blockers:
        # Top blocker is potential (unclear) - use second if available
        if len(blockers) > 1:
            top_blocker = blockers[1]
            label = top_blocker.get("label", "Issue")
            reason_line, _ = _get_template(top_blocker.get("id"), top_blocker.get("status"))
            reason_line = _normalize_encoding_artifacts(reason_line)
            verdict = f"The main barrier to conversion is **{label}**: {reason_line.lower()}."
        else:
            verdict = "The page shows good conversion fundamentals, with minor areas for improvement."
    else:
        verdict = "The page shows good conversion fundamentals, with minor areas for improvement."
    
    verdict = _normalize_encoding_artifacts(verdict)
    report_lines.append("## Verdict")
    report_lines.append("")
    report_lines.append(verdict)
    report_lines.append("")
    
    # B) Top blockers (3 bullets)
    report_lines.append("## Top Blockers")
    report_lines.append("")
    
    for blocker in blockers[:3]:
        label = blocker.get("label", "Issue")
        is_potential = blocker.get("is_potential", False)
        reason_line, action_line = _get_template(blocker.get("id"), blocker.get("status"))
        
        # Normalize encoding artifacts in template text
        reason_line = _normalize_encoding_artifacts(reason_line)
        action_line = _normalize_encoding_artifacts(action_line)
        
        # Label potential issues
        if is_potential:
            label = f"{label} (Potential Issue - Low Evidence)"
        
        report_lines.append(f"- **{label}** - {reason_line}")
        quick_wins.append(action_line)
    
    report_lines.append("")
    
    # C) Why users hesitate (2-3 sentences combining top blockers)
    report_lines.append("## Why Users Hesitate")
    report_lines.append("")
    
    # Filter out potential issues for "Why Users Hesitate" section
    confirmed_blockers = [b for b in blockers if not b.get("is_potential", False)]
    
    if len(confirmed_blockers) >= 2:
        reason1, _ = _get_template(confirmed_blockers[0].get("id"), confirmed_blockers[0].get("status"))
        reason2, _ = _get_template(confirmed_blockers[1].get("id"), confirmed_blockers[1].get("status"))
        reason1 = _normalize_encoding_artifacts(reason1)
        reason2 = _normalize_encoding_artifacts(reason2)
        
        hesitate_text = (
            f"Users hesitate because {reason1.lower()}. "
            f"Additionally, {reason2.lower()}. "
        )
        
        if len(confirmed_blockers) >= 3:
            reason3, _ = _get_template(confirmed_blockers[2].get("id"), confirmed_blockers[2].get("status"))
            reason3 = _normalize_encoding_artifacts(reason3)
            hesitate_text += f"Finally, {reason3.lower()}."
        else:
            hesitate_text += "These issues create friction that prevents users from taking action."
    elif len(confirmed_blockers) == 1:
        reason, _ = _get_template(confirmed_blockers[0].get("id"), confirmed_blockers[0].get("status"))
        reason = _normalize_encoding_artifacts(reason)
        hesitate_text = (
            f"Users hesitate because {reason.lower()}. "
            "This creates friction that prevents users from taking action."
        )
    else:
        hesitate_text = "The page shows good fundamentals, but minor improvements could further reduce hesitation."
    
    hesitate_text = _normalize_encoding_artifacts(hesitate_text)
    report_lines.append(hesitate_text)
    report_lines.append("")
    
    # D) Quick wins (3-5 items)
    report_lines.append("## Quick Wins")
    report_lines.append("")
    
    # Add action lines from blockers first
    all_actions = quick_wins.copy()
    
    # Get additional actions from other high-severity signals
    for signal in signals:
        if signal.get("id") not in blocker_ids:
            status = signal.get("status", "unclear")
            if status in ["missing", "weak"]:
                _, action_line = _get_template(signal.get("id"), status)
                if action_line and action_line not in all_actions:
                    all_actions.append(action_line)
                    if len(all_actions) >= 5:
                        break
    
    # Ensure we have at least 3, max 5
    quick_wins_final = all_actions[:5]
    if len(quick_wins_final) < 3:
        # Add generic quick wins if needed
        quick_wins_final.extend([
            "Review and simplify page structure",
            "Test different headline variations",
            "Add clear value proposition"
        ])
        quick_wins_final = quick_wins_final[:5]
    
    for i, action in enumerate(quick_wins_final, 1):
        report_lines.append(f"{i}. {action}")
    
    report_lines.append("")
    
    # E) Suggested rewrites
    report_lines.append("## Suggested Rewrites")
    report_lines.append("")
    
    # Headline suggestion
    value_prop_presence = signal_dict.get("value_prop_presence", {})
    value_prop_specificity = signal_dict.get("value_prop_specificity", {})
    
    has_headline_issue = False
    if value_prop_presence.get("status") in ["missing", "weak"] or \
       value_prop_specificity.get("status") in ["vague", "mixed", "missing", "weak"]:
        has_headline_issue = True
        report_lines.append("### Headline")
        report_lines.append("")
        report_lines.append("**Current issue:** Value proposition is unclear or vague")
        report_lines.append("")
        report_lines.append("**Suggested:** Create a headline that clearly states:")
        report_lines.append("- Who you help (target audience)")
        report_lines.append("- What outcome they get")
        report_lines.append("- What problem you solve")
        report_lines.append("")
        report_lines.append("**Example:** \"[Tool] helps [audience] [outcome] by [problem solved]\"")
        report_lines.append("")
    
    # CTA suggestion
    cta_clarity = signal_dict.get("cta_clarity", {})
    cta_competition = signal_dict.get("cta_competition", {})
    
    has_cta_issue = False
    if cta_clarity.get("status") in ["missing", "weak"] or \
       cta_competition.get("status") in ["missing", "weak"]:
        has_cta_issue = True
        report_lines.append("### CTA")
        report_lines.append("")
        if cta_clarity.get("status") in ["missing", "weak"]:
            report_lines.append("**Current issue:** CTA is vague or doesn't state the outcome")
            report_lines.append("")
            report_lines.append("**Suggested:** Use outcome-focused CTAs:")
            report_lines.append("- ✅ \"Get Your Report\" (not \"Submit\")")
            report_lines.append("- ✅ \"Start Analysis\" (not \"Click Here\")")
            report_lines.append("- ✅ \"Try Free Trial\" (not \"Continue\")")
        if cta_competition.get("status") in ["missing", "weak"]:
            report_lines.append("")
            report_lines.append("**Current issue:** Too many CTAs competing for attention")
            report_lines.append("")
            report_lines.append("**Suggested:** Focus on 1 primary CTA above the fold")
        
        report_lines.append("")
    
    if not has_headline_issue and not has_cta_issue:
        report_lines.append("No rewrite suggestions - current copy is effective.")
        report_lines.append("")
    
    # F) Checklist
    report_lines.append("## Checklist")
    report_lines.append("")
    
    for action in quick_wins_final:
        report_lines.append(f"- [ ] {action}")
    
    report_lines.append("")
    
    # Join all lines
    human_report = "\n".join(report_lines)
    
    # Normalize encoding artifacts (fix mojibake)
    human_report = _normalize_encoding_artifacts(human_report)
    
    return {
        "human_report": human_report,
        "report_meta": {
            "blockers": blocker_ids,
            "quick_wins": quick_wins_final
        }
    }
