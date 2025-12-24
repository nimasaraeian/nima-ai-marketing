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

# Signal importance weights based on category impact on decision-making
# Higher weight = higher impact on conversion decisions
SIGNAL_IMPORTANCE_WEIGHTS = {
    # CLARITY category (35% weight)
    "value_prop_presence": 100,      # Highest impact - core value proposition
    "value_prop_specificity": 85,    # High impact - specificity drives clarity
    "information_hierarchy": 75,     # High impact - guides user attention
    # ACTION category (25% weight)
    "primary_cta_presence": 95,      # Very high impact - no CTA = no action
    "cta_clarity": 80,               # High impact - unclear CTAs reduce conversions
    "cta_competition": 70,           # Medium-high impact - too many CTAs cause confusion
    # TRUST category (25% weight)
    "social_proof_presence": 90,     # Very high impact - trust is critical
    "risk_reducers": 85,             # High impact - reduces perceived risk
    "legitimacy_signals": 65,        # Medium impact - important but less critical
    # FRICTION category (15% weight)
    "pricing_visibility": 80,        # High impact - pricing clarity reduces friction
    "cognitive_load": 70,            # Medium-high impact - overload hurts decisions
    "form_friction": 60,             # Medium impact - can be mitigated with other fixes
}

# Safe generic templates for fallback (max 25 words each)
SAFE_TEMPLATE = {
    "reason_line": "This area may be blocking decisions.",
    "action_line": "Add or adjust this element."
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
        "reason_line": "Users don't understand what you offer, blocking decisions.",
        "action_line": "Add clear value proposition stating who you help and what outcome you deliver."
    },
    ("value_prop_presence", "weak"): {
        "reason_line": "Generic value proposition fails to connect with users, causing hesitation.",
        "action_line": "Make value proposition specific with concrete benefits and target audience."
    },
    ("value_prop_presence", "unclear"): {
        "reason_line": "Value proposition clarity is uncertain and may be blocking decisions.",
        "action_line": "Review and clarify your value proposition to ensure it's specific and clear."
    },
    # Value Proposition Specificity
    ("value_prop_specificity", "missing"): {
        "reason_line": "Vague language without specifics creates uncertainty, blocking decisions.",
        "action_line": "Replace vague claims with specific numbers, results, and concrete details."
    },
    ("value_prop_specificity", "weak"): {
        "reason_line": "Mixed specific and vague language reduces trust and blocks decisions.",
        "action_line": "Replace remaining vague terms with specific numbers and measurable results."
    },
    ("value_prop_specificity", "unclear"): {
        "reason_line": "Value proposition specificity is uncertain and may block decisions.",
        "action_line": "Review value proposition and add specific details with numbers or results."
    },
    # Information Hierarchy
    ("information_hierarchy", "missing"): {
        "reason_line": "No clear hierarchy confuses users about what to read first, blocking decisions.",
        "action_line": "Add H1 headline and clear CTA to establish visual information hierarchy."
    },
    ("information_hierarchy", "weak"): {
        "reason_line": "Incomplete hierarchy makes it unclear what users should focus on first.",
        "action_line": "Create clear hierarchy: H1 headline, then supporting text, then CTA button."
    },
    ("information_hierarchy", "unclear"): {
        "reason_line": "Information hierarchy clarity is uncertain and may block user decisions.",
        "action_line": "Review page structure and ensure clear visual hierarchy from top to bottom."
    },
    # Primary CTA Presence
    ("primary_cta_presence", "missing"): {
        "reason_line": "No clear call-to-action means users don't know what action to take.",
        "action_line": "Add prominent primary CTA button with action verbs like Start, Get, or Try."
    },
    ("primary_cta_presence", "weak"): {
        "reason_line": "No visible CTA button confuses users about how to proceed, blocking decisions.",
        "action_line": "Add a prominent, action-oriented CTA button like Get Started or Try Now."
    },
    ("primary_cta_presence", "unclear"): {
        "reason_line": "Primary CTA presence is uncertain and may be blocking user decisions.",
        "action_line": "Review page and add a prominent primary CTA button if one is missing."
    },
    # CTA Clarity
    ("cta_clarity", "missing"): {
        "reason_line": "Vague CTAs don't communicate the outcome, creating uncertainty that blocks decisions.",
        "action_line": "Replace vague CTAs with outcome-focused ones like Get Report or Start Analysis."
    },
    ("cta_clarity", "weak"): {
        "reason_line": "Some vague CTAs like Submit or Click Here don't communicate value, blocking decisions.",
        "action_line": "Make all CTAs outcome-focused, using Get Report instead of Submit, for example."
    },
    ("cta_clarity", "unclear"): {
        "reason_line": "CTA clarity is uncertain and vague buttons may be blocking user decisions.",
        "action_line": "Review CTA text and ensure each button clearly states the specific outcome users get."
    },
    # CTA Competition
    ("cta_competition", "missing"): {
        "reason_line": "Too many CTAs compete for attention, creating confusion that blocks decisions.",
        "action_line": "Focus on one primary action and remove or de-emphasize competing CTAs."
    },
    ("cta_competition", "weak"): {
        "reason_line": "Multiple CTAs in hero section create moderate competition and decision paralysis.",
        "action_line": "Reduce to one primary CTA in the hero section for clearer focus."
    },
    ("cta_competition", "unclear"): {
        "reason_line": "CTA competition level is uncertain and may be blocking user decisions.",
        "action_line": "Review CTA count and placement to ensure one clear primary action stands out."
    },
    # Social Proof Presence
    ("social_proof_presence", "missing"): {
        "reason_line": "No social proof reduces trust and makes users hesitate to decide.",
        "action_line": "Add testimonials, customer reviews, logos, or a trusted by section."
    },
    ("social_proof_presence", "weak"): {
        "reason_line": "Limited social proof weakens trust signals and blocks user decisions.",
        "action_line": "Add more testimonials, reviews, customer logos, or trusted by badges."
    },
    ("social_proof_presence", "unclear"): {
        "reason_line": "Social proof presence is uncertain and lack of trust may block decisions.",
        "action_line": "Review page and add social proof like testimonials or customer logos if missing."
    },
    # Risk Reducers
    ("risk_reducers", "missing"): {
        "reason_line": "No risk reduction signals increase perceived risk and block user decisions.",
        "action_line": "Add free trial, money-back guarantee, or cancel anytime messaging."
    },
    ("risk_reducers", "weak"): {
        "reason_line": "Limited risk reduction signals don't adequately address user concerns about risk.",
        "action_line": "Add more risk reduction like free trials, guarantees, or flexible cancellation terms."
    },
    ("risk_reducers", "unclear"): {
        "reason_line": "Risk reduction signals are uncertain and perceived risk may block decisions.",
        "action_line": "Review page and add risk reduction messaging like guarantees or trials if missing."
    },
    # Legitimacy Signals
    ("legitimacy_signals", "missing"): {
        "reason_line": "Missing legitimacy signals like contact info and policies reduce trust and block decisions.",
        "action_line": "Add contact information, about page, privacy policy, and terms of service links."
    },
    ("legitimacy_signals", "weak"): {
        "reason_line": "Limited legitimacy indicators weaken credibility and make users hesitate to decide.",
        "action_line": "Add more legitimacy signals like contact info, privacy policy, and terms of service."
    },
    ("legitimacy_signals", "unclear"): {
        "reason_line": "Legitimacy signals are uncertain and lack of credibility may block decisions.",
        "action_line": "Review page and add legitimacy signals like contact info and policies if missing."
    },
    # Pricing Visibility
    ("pricing_visibility", "missing"): {
        "reason_line": "Hidden pricing creates uncertainty about cost and blocks user decisions.",
        "action_line": "Add clear, visible pricing information to reduce friction and build trust."
    },
    ("pricing_visibility", "weak"): {
        "reason_line": "Unclear pricing path creates friction and makes users hesitate to decide.",
        "action_line": "Make pricing more prominent and clearly visible to reduce decision friction."
    },
    ("pricing_visibility", "unclear"): {
        "reason_line": "Pricing visibility is uncertain and hidden pricing may block user decisions.",
        "action_line": "Review page and ensure pricing is clearly visible and easy to find."
    },
    # Form Friction
    ("form_friction", "missing"): {
        "reason_line": "Complex forms or forms shown too early create friction that blocks decisions.",
        "action_line": "Simplify the form or move it after communicating value to users."
    },
    ("form_friction", "weak"): {
        "reason_line": "Moderate form complexity creates unnecessary friction and blocks user decisions.",
        "action_line": "Simplify the form to only ask for essential information required to proceed."
    },
    ("form_friction", "unclear"): {
        "reason_line": "Form friction level is uncertain and complexity may be blocking decisions.",
        "action_line": "Review form complexity and placement to ensure it doesn't create unnecessary friction."
    },
    # Cognitive Load
    ("cognitive_load", "missing"): {
        "reason_line": "High cognitive load from too much text and unclear hierarchy blocks decisions.",
        "action_line": "Reduce text, use clear H1 and H2 headings, and remove conflicting messages."
    },
    ("cognitive_load", "weak"): {
        "reason_line": "Moderate cognitive load from organization issues creates confusion and blocks decisions.",
        "action_line": "Simplify content, improve hierarchy with clear headings, and remove conflicting messages."
    },
    ("cognitive_load", "unclear"): {
        "reason_line": "Cognitive load level is uncertain and information overload may block decisions.",
        "action_line": "Review content organization, simplify where possible, and ensure clear visual hierarchy."
    },
}


def _count_words(text: str) -> int:
    """
    Count words in a text string.
    
    Args:
        text: Text string to count words in
    
    Returns:
        Number of words
    """
    if not text or not text.strip():
        return 0
    return len(text.strip().split())


def _validate_word_count(text: str, max_words: int, field_name: str) -> str:
    """
    Validate and truncate text to max word count.
    
    Args:
        text: Text to validate
        max_words: Maximum allowed words
        field_name: Name of the field for error messages
    
    Returns:
        Text truncated to max_words if needed
    """
    word_count = _count_words(text)
    if word_count > max_words:
        words = text.strip().split()
        truncated = " ".join(words[:max_words])
        # Log warning in production code would go here
        return truncated
    return text


# LEGACY_MODE_ENABLED = False  # Set to True only for backward compatibility
LEGACY_MODE_ENABLED = False  # DISABLED - use human_report_v2 pipeline instead

def _generate_emotional_verdict(signal_id: str, status: str) -> str:
    """
    LEGACY FUNCTION - DISABLED by default.
    
    Generate emotional/cognitive verdict focusing on how the page feels to users.
    This function is disabled in favor of human_report_v2 pipeline.
    
    Args:
        signal_id: Signal identifier
        status: Signal status (missing, weak, unclear)
    
    Returns:
        Verdict string (1-2 sentences) focusing on emotional/cognitive hesitation
    """
    if not LEGACY_MODE_ENABLED:
        # Return empty string - legacy generator disabled
        return ""
    # Map signal IDs to emotional/cognitive hesitation patterns
    # Format: "Users hesitate because the page feels [emotion] within the first seconds."
    
    verdict_templates = {
        "value_prop_presence": {
            "missing": "Users hesitate because the page feels unclear and confusing within the first seconds.",
            "weak": "Users hesitate because the page feels vague and disconnected from their needs.",
            "unclear": "Users hesitate because the page feels uncertain about what it offers."
        },
        "value_prop_specificity": {
            "missing": "Users hesitate because the page feels too generic and lacks credibility.",
            "weak": "Users hesitate because the page feels partly vague and unconvincing.",
            "unclear": "Users hesitate because the page feels uncertain in its messaging."
        },
        "information_hierarchy": {
            "missing": "Users hesitate because the page feels overwhelming and chaotic within the first seconds.",
            "weak": "Users hesitate because the page feels disorganized and hard to scan.",
            "unclear": "Users hesitate because the page feels confusing about what to focus on."
        },
        "primary_cta_presence": {
            "missing": "Users hesitate because the page feels incomplete and unclear about what action to take.",
            "weak": "Users hesitate because the page feels uncertain about the next step.",
            "unclear": "Users hesitate because the page feels ambiguous about how to proceed."
        },
        "cta_clarity": {
            "missing": "Users hesitate because the page feels vague about what happens after they click.",
            "weak": "Users hesitate because the page feels unclear about the outcome they'll get.",
            "unclear": "Users hesitate because the page feels uncertain about the action outcome."
        },
        "cta_competition": {
            "missing": "Users hesitate because the page feels overwhelming with too many choices.",
            "weak": "Users hesitate because the page feels confusing about which action to take.",
            "unclear": "Users hesitate because the page feels cluttered with competing options."
        },
        "social_proof_presence": {
            "missing": "Users hesitate because the page feels untrustworthy and unproven within the first seconds.",
            "weak": "Users hesitate because the page feels uncertain about credibility and trust.",
            "unclear": "Users hesitate because the page feels lacking in social validation."
        },
        "risk_reducers": {
            "missing": "Users hesitate because the page feels risky and unsafe to commit.",
            "weak": "Users hesitate because the page feels uncertain about risk protection.",
            "unclear": "Users hesitate because the page feels unclear about safety guarantees."
        },
        "legitimacy_signals": {
            "missing": "Users hesitate because the page feels sketchy and unprofessional within the first seconds.",
            "weak": "Users hesitate because the page feels uncertain about legitimacy and credibility.",
            "unclear": "Users hesitate because the page feels lacking in professional trust signals."
        },
        "pricing_visibility": {
            "missing": "Users hesitate because the page feels secretive and uncertain about cost.",
            "weak": "Users hesitate because the page feels unclear about pricing and value.",
            "unclear": "Users hesitate because the page feels ambiguous about financial commitment."
        },
        "form_friction": {
            "missing": "Users hesitate because the page feels burdensome and overwhelming with complex requirements.",
            "weak": "Users hesitate because the page feels like too much effort to complete.",
            "unclear": "Users hesitate because the page feels uncertain about the effort required."
        },
        "cognitive_load": {
            "missing": "Users hesitate because the page feels overwhelming and exhausting within the first seconds.",
            "weak": "Users hesitate because the page feels mentally tiring and hard to process.",
            "unclear": "Users hesitate because the page feels like too much information to handle."
        }
    }
    
    # Get the appropriate template
    signal_templates = verdict_templates.get(signal_id, {})
    verdict = signal_templates.get(status)
    
    # Fallback if signal_id or status not found
    if not verdict:
        if status == "unclear":
            verdict = "Users hesitate because the page feels uncertain about key elements."
        else:
            verdict = "Users hesitate because the page feels unclear and unconvincing within the first seconds."
    
    return verdict


def _is_valid_quick_win(action: str) -> bool:
    """
    Validate if a quick win is suitable for the Quick Wins section.
    
    Criteria:
    - Must be UI, copy, or trust related (not process-related)
    - Must be executable in under 30 minutes
    - Must not be generic or vague
    
    Args:
        action: Action string to validate
    
    Returns:
        True if valid quick win, False otherwise
    """
    if not action or len(action.strip()) < 10:
        return False
    
    action_lower = action.lower().strip()
    
    # Reject actions that start with generic/vague process verbs (not executable)
    generic_starters = [
        "review",
        "test different",
        "consider",
        "evaluate",
        "analyze",
        "assess",
        "check",
        "examine",
        "investigate"
    ]
    
    # Check if action starts with generic verb
    starts_with_generic = False
    for starter in generic_starters:
        if action_lower.startswith(starter):
            starts_with_generic = True
            break
    
    # If starts with generic verb, check if it has concrete action after "and" or "to"
    if starts_with_generic:
        has_concrete_action = False
        actionable_verbs = ["add", "replace", "make", "simplify", "remove", "update", "change", "create", "reduce", "improve", "ensure", "include"]
        
        # Check " and " pattern
        if " and " in action_lower:
            parts = action_lower.split(" and ", 1)
            if len(parts) > 1:
                second_part = parts[1].strip()
                if any(second_part.startswith(verb + " ") or second_part.startswith(verb) for verb in actionable_verbs):
                    has_concrete_action = True
        
        # Check " to " pattern
        if not has_concrete_action and " to " in action_lower:
            to_parts = action_lower.split(" to ", 1)
            if len(to_parts) > 1:
                after_to = to_parts[1].strip()
                if any(after_to.startswith(verb + " ") or after_to.startswith(verb) for verb in actionable_verbs):
                    has_concrete_action = True
        
        # Reject if no concrete action found
        if not has_concrete_action:
            return False
    
    # Must start with actionable verb (UI/copy/trust related)
    actionable_verbs = [
        "add",
        "replace",
        "make",
        "simplify",
        "remove",
        "update",
        "change",
        "create",
        "reduce",
        "improve",
        "ensure",
        "include"
    ]
    
    has_actionable_verb = any(action_lower.startswith(verb) for verb in actionable_verbs)
    
    # Reject if it ends with vague/testing patterns (indicates long process)
    vague_endings = [
        "then retest",
        "then test",
        "and retest",
        "if missing",
        "if needed"
    ]
    
    has_vague_ending = any(action_lower.endswith(ending) for ending in vague_endings)
    
    # Quick wins must be specific and executable (at least 5 words)
    is_specific = len(action.split()) >= 5
    
    return has_actionable_verb and is_specific and not has_vague_ending


def _is_duplicate_quick_win(action: str, existing_actions: List[str]) -> bool:
    """
    Check if a quick win is a duplicate of existing ones.
    
    Args:
        action: Action string to check
        existing_actions: List of existing action strings
    
    Returns:
        True if duplicate, False otherwise
    """
    action_lower = action.lower().strip()
    
    for existing in existing_actions:
        existing_lower = existing.lower().strip()
        
        # Check if actions are very similar (same core verb and similar target)
        action_words = set(action_lower.split()[:5])  # First 5 words
        existing_words = set(existing_lower.split()[:5])
        
        # If more than 3 words overlap, consider it a duplicate
        overlap = len(action_words.intersection(existing_words))
        if overlap >= 3:
            return True
    
    return False


def _generate_copy_suggestions(
    blockers: List[Dict[str, Any]],
    signal_dict: Dict[str, Dict[str, Any]]
) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate outcome-driven H1 and CTA copy suggestions based on detected blockers.
    
    Returns concrete, action-oriented copy (not templates).
    
    Args:
        blockers: List of top blockers
        signal_dict: Dictionary of all signals by ID
    
    Returns:
        Tuple of (H1 suggestion, CTA suggestion) - both can be None if no suggestions needed
    """
    h1_suggestion = None
    cta_suggestion = None
    
    # Check if we need H1 suggestion (value prop issues)
    value_prop_presence = signal_dict.get("value_prop_presence", {})
    value_prop_specificity = signal_dict.get("value_prop_specificity", {})
    
    needs_h1 = value_prop_presence.get("status") in ["missing", "weak"] or \
               value_prop_specificity.get("status") in ["missing", "weak"]
    
    if needs_h1:
        # Generate outcome-driven H1 - focus on what user gets (concrete, not template)
        # Base suggestion on top blocker if available
        if blockers:
            top_blocker_id = blockers[0].get("id")
            if top_blocker_id == "pricing_visibility":
                h1_suggestion = "See What You Get and How Much It Costs"
            elif top_blocker_id in ["social_proof_presence", "legitimacy_signals"]:
                h1_suggestion = "Join Thousands Getting Results Every Day"
            elif top_blocker_id == "cognitive_load":
                h1_suggestion = "Get the One Thing That Solves Your Problem"
            else:
                h1_suggestion = "Get Results in Less Time with Less Effort"
        else:
            h1_suggestion = "Get the Results You Need Faster"
    
    # Check if we need CTA suggestion (CTA clarity or competition issues)
    cta_clarity = signal_dict.get("cta_clarity", {})
    cta_competition = signal_dict.get("cta_competition", {})
    primary_cta_presence = signal_dict.get("primary_cta_presence", {})
    
    needs_cta = cta_clarity.get("status") in ["missing", "weak"] or \
                cta_competition.get("status") in ["missing", "weak"] or \
                primary_cta_presence.get("status") in ["missing", "weak"]
    
    if needs_cta:
        # Generate outcome-driven CTA - focus on action and outcome
        # Prioritize based on top blocker
        if blockers:
            top_blocker_id = blockers[0].get("id")
            if top_blocker_id in ["social_proof_presence", "risk_reducers", "legitimacy_signals"]:
                cta_suggestion = "Start Free Trial"
            elif top_blocker_id == "pricing_visibility":
                cta_suggestion = "See Pricing Now"
            elif top_blocker_id == "form_friction":
                cta_suggestion = "Get Started"
            elif top_blocker_id == "cta_clarity":
                cta_suggestion = "Get Your Results"
            else:
                cta_suggestion = "Get Started Today"
        else:
            cta_suggestion = "Get Started"
    
    return h1_suggestion, cta_suggestion


def _extract_checklist_item(action: str) -> str:
    """
    Extract short, binary checklist item from action description.
    
    Removes explanations and keeps only the core action (verb + key noun).
    
    Args:
        action: Full action description
    
    Returns:
        Short checklist item (e.g., "Add primary CTA" from "Add prominent primary CTA button with action verbs")
    """
    if not action:
        return ""
    
    words = action.split()
    
    if len(words) < 2:
        return action[:40]
    
    # Stop words that indicate explanation/details are coming
    stop_words = {"with", "and", "or", "to", "for", "like", "such", "as", "in", "on", "by"}
    
    # Extract verb + up to 3 more words (2-4 words total)
    core_words = [words[0]]  # Start with verb
    
    for i in range(1, min(4, len(words))):
        word_lower = words[i].lower().rstrip('.,;:')
        
        # Stop at stop words (indicates explanation/details)
        if word_lower in stop_words:
            break
        
        core_words.append(words[i])
        
        # Common patterns: stop after finding key terms
        if word_lower in {"cta", "button", "headline", "h1", "testimonials", "reviews", 
                          "pricing", "form", "guarantee", "trial", "logos", "proof"}:
            # Check if next word is also important (e.g., "value proposition")
            if i + 1 < len(words) and words[i+1].lower() not in stop_words:
                # Might include next word for compound terms
                if word_lower in {"value", "primary", "social"}:
                    continue
            break
    
    result = " ".join(core_words)
    # Capitalize first letter
    return result[0].upper() + result[1:] if result else action[:40]


def _generate_checklist_items(quick_wins: List[str], max_items: int = 4) -> List[str]:
    """
    Generate short, binary checklist items from quick wins.
    
    Args:
        quick_wins: List of quick win action descriptions
        max_items: Maximum number of checklist items (default: 4)
    
    Returns:
        List of short checklist items (max max_items)
    """
    checklist_items = []
    
    for action in quick_wins[:max_items]:
        item = _extract_checklist_item(action)
        if item:
            checklist_items.append(item)
    
    return checklist_items


def _filter_and_prioritize_quick_wins(
    actions: List[str],
    target_count: int = 3
) -> List[str]:
    """
    Filter and prioritize quick wins to return exactly target_count items.
    
    Rules:
    - Only include UI, copy, or trust related actions
    - Only include actions executable in under 30 minutes
    - Remove generic, vague, or duplicated suggestions
    - Prioritize actions from top blockers
    
    Args:
        actions: List of action strings
        target_count: Target number of quick wins (default: 3)
    
    Returns:
        List of exactly target_count valid quick wins
    """
    # Filter valid quick wins
    valid_actions = [a for a in actions if _is_valid_quick_win(a)]
    
    # Remove duplicates while preserving order
    unique_actions = []
    for action in valid_actions:
        if not _is_duplicate_quick_win(action, unique_actions):
            unique_actions.append(action)
    
    # Return exactly target_count items (or fewer if not enough valid ones)
    return unique_actions[:target_count]


def _get_template(signal_id: str, status: str) -> Tuple[str, str]:
    """
    Get template for signal.id + status.
    Always returns a tuple (reason_line, action_line) - never empty.
    Enforces max 25 words per field.
    """
    key = (signal_id, status)
    if key in SIGNAL_TEMPLATES:
        template = SIGNAL_TEMPLATES[key]
        reason_line = _validate_word_count(template["reason_line"], 25, "reason_line")
        action_line = _validate_word_count(template["action_line"], 25, "action_line")
        return reason_line, action_line
    
    # Safe fallback - never return empty
    reason_line = _validate_word_count(SAFE_TEMPLATE["reason_line"], 25, "reason_line")
    action_line = _validate_word_count(SAFE_TEMPLATE["action_line"], 25, "action_line")
    return reason_line, action_line


def _calculate_decision_impact_score(
    signal_id: str,
    status: str,
    confidence: float
) -> float:
    """
    Calculate decision impact score for a signal/blocker.
    
    Decision impact score combines:
    - Signal importance (how critical this signal is for conversion)
    - Severity (missing > weak > unclear)
    - Confidence (higher confidence in detection = higher impact if it's a real issue)
    
    Args:
        signal_id: Signal identifier
        status: Signal status (missing, weak, unclear, present)
        confidence: Confidence level (0.0-1.0)
    
    Returns:
        Decision impact score (0-100, higher = more impactful blocker)
    """
    # Get signal importance (0-100)
    signal_importance = SIGNAL_IMPORTANCE_WEIGHTS.get(signal_id, 50)  # Default to 50 if unknown
    
    # Get severity multiplier
    severity_multiplier = SEVERITY_WEIGHTS.get(status, 0) / 3.0  # Normalize to 0-1
    
    # If status is "present", impact score is 0 (not a blocker)
    if status == "present" or severity_multiplier == 0:
        return 0.0
    
    # Confidence adjustment:
    # - Higher confidence in detecting a real issue = higher impact
    # - For unclear status, lower confidence reduces impact
    if status == "unclear":
        confidence_adjustment = confidence * 0.5  # Unclear issues have lower impact
    else:
        confidence_adjustment = 0.5 + (confidence * 0.5)  # 0.5-1.0 range for missing/weak
    
    # Calculate decision impact score
    # Formula: signal_importance * severity_multiplier * confidence_adjustment
    impact_score = signal_importance * severity_multiplier * confidence_adjustment
    
    # Normalize to 0-100 range
    return min(100.0, max(0.0, impact_score))


def rank_blockers(signals: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Rank all detected issues by decision impact score and return top 3 blockers.
    
    Rules:
    - All issues (missing, weak, unclear) are ranked by decision impact score
    - Returns top 3 blockers by decision impact score
    - Remaining issues are stored internally (returned as second element of tuple)
    - Never allows "unclear" issues to be #1 if there are "missing" or "weak" issues
    
    Args:
        signals: List of signal dictionaries with id, status, confidence
    
    Returns:
        Tuple of:
        - Top 3 blockers (list of dicts with: id, status, decision_impact_score, confidence, is_potential)
        - Remaining blockers stored internally (not to be exposed to user)
    """
    all_blockers = []
    
    # Calculate decision impact score for all issues (excluding "present" status)
    for signal in signals:
        status = signal.get("status", "unclear")
        confidence = signal.get("confidence", 0.5)
        signal_id = signal.get("id")
        
        # Skip signals that are "present" (not blockers)
        if status == "present":
            continue
        
        # Calculate decision impact score
        impact_score = _calculate_decision_impact_score(signal_id, status, confidence)
        
        # Only include issues with impact score > 0
        if impact_score > 0:
            is_potential = (status == "unclear")
            all_blockers.append({
                "id": signal_id,
                "status": status,
                "decision_impact_score": impact_score,
                "confidence": confidence,
                "is_potential": is_potential,
                # Keep original signal data for reference
                "original_signal": signal
            })
    
    # Sort all blockers by decision impact score (highest first)
    all_blockers.sort(key=lambda x: x["decision_impact_score"], reverse=True)
    
    # Separate eligible blockers (missing/weak) from potential (unclear)
    eligible_blockers = [b for b in all_blockers if not b["is_potential"]]
    potential_blockers = [b for b in all_blockers if b["is_potential"]]
    
    # Take top 3 blockers
    top_blockers = []
    
    # First, add eligible blockers (missing/weak) - these are confirmed issues
    if eligible_blockers:
        top_blockers = eligible_blockers[:3]
    
    # If we have fewer than 3 eligible blockers, we can add potential blockers
    # but only if we already have at least 1 eligible (so unclear is never #1)
    if len(top_blockers) < 3 and potential_blockers and len(top_blockers) > 0:
        needed = 3 - len(top_blockers)
        top_blockers.extend(potential_blockers[:needed])
    
    # Store remaining blockers internally (not to be exposed to user)
    top_blocker_ids = {b["id"] for b in top_blockers}
    remaining_blockers = [b for b in all_blockers if b["id"] not in top_blocker_ids]
    
    return top_blockers, remaining_blockers


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
    # Rank blockers by decision impact score (returns top 3 + remaining blockers internally)
    top_blockers, remaining_blockers = rank_blockers(signals)
    blocker_ids = [b["id"] for b in top_blockers]
    
    # Get blocker signals (only top 3 blockers for user display)
    signal_dict = {s["id"]: s for s in signals}
    blockers = []
    for blocker_info in top_blockers:
        signal_id = blocker_info["id"]
        if signal_id in signal_dict:
            signal = signal_dict[signal_id].copy()
            signal["is_potential"] = blocker_info.get("is_potential", False)
            signal["decision_impact_score"] = blocker_info.get("decision_impact_score", 0)
            blockers.append(signal)
    
    # Build report sections
    report_lines = []
    quick_wins = []
    
    # A) Verdict (1-2 sentences focused on emotional/cognitive hesitation)
    if blockers and not blockers[0].get("is_potential", False):
        top_blocker = blockers[0]
        signal_id = top_blocker.get("id")
        status = top_blocker.get("status", "missing")
        verdict = _generate_emotional_verdict(signal_id, status)
    elif blockers:
        # Top blocker is potential (unclear) - use second if available
        if len(blockers) > 1:
            top_blocker = blockers[1]
            signal_id = top_blocker.get("id")
            status = top_blocker.get("status", "missing")
            verdict = _generate_emotional_verdict(signal_id, status)
        else:
            # Use the unclear blocker but with a softer tone
            top_blocker = blockers[0]
            signal_id = top_blocker.get("id")
            verdict = _generate_emotional_verdict(signal_id, "unclear")
    else:
        verdict = "The page feels clear and trustworthy, with good fundamentals overall."
    
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
    
    # D) Quick wins (exactly 3 items)
    report_lines.append("## Quick Wins")
    report_lines.append("")
    
    # Collect action lines from top blockers first (prioritized)
    all_actions = quick_wins.copy()
    
    # Get additional actions from other high-severity signals (missing/weak only)
    for signal in signals:
        if signal.get("id") not in blocker_ids:
            status = signal.get("status", "unclear")
            if status in ["missing", "weak"]:
                _, action_line = _get_template(signal.get("id"), status)
                if action_line:
                    all_actions.append(action_line)
    
    # Filter and prioritize to get exactly 3 valid quick wins
    quick_wins_final = _filter_and_prioritize_quick_wins(all_actions, target_count=3)
    
    # If we have fewer than 3 after filtering, use the top valid ones we have
    # (better to have 1-2 good ones than generic filler)
    for i, action in enumerate(quick_wins_final, 1):
        report_lines.append(f"{i}. {action}")
    
    report_lines.append("")
    
    # E) Suggested Copy (only final recommended versions)
    h1_suggestion, cta_suggestion = _generate_copy_suggestions(blockers, signal_dict)
    
    if h1_suggestion or cta_suggestion:
        report_lines.append("## Suggested Copy")
        report_lines.append("")
        
        if h1_suggestion:
            report_lines.append(f"**H1:** {h1_suggestion}")
            report_lines.append("")
        
        if cta_suggestion:
            report_lines.append(f"**Primary CTA:** {cta_suggestion}")
            report_lines.append("")
    
    # F) Checklist (max 3-4 binary items, no explanations)
    report_lines.append("## Checklist")
    report_lines.append("")
    
    checklist_items = _generate_checklist_items(quick_wins_final, max_items=4)
    
    for item in checklist_items:
        report_lines.append(f"- [ ] {item}")
    
    report_lines.append("")
    
    # Join all lines
    human_report = "\n".join(report_lines)
    
    # Normalize encoding artifacts (fix mojibake)
    human_report = _normalize_encoding_artifacts(human_report)
    
    # Store remaining blockers internally (not exposed to user)
    remaining_blocker_ids = [b["id"] for b in remaining_blockers]
    
    return {
        "human_report": human_report,
        "report_meta": {
            "blockers": blocker_ids,  # Top 3 blockers shown to user
            "blockers_internal": remaining_blocker_ids,  # Remaining blockers stored internally
            "quick_wins": quick_wins_final
        }
    }
