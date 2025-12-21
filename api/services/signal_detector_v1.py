import re
from typing import Any, Dict, List, Optional
from ..schemas.signal_v1 import SignalReportV1, CTAItem, EvidenceItem


ACTION_VERBS = re.compile(r"\b(get|start|try|book|request|download|see|view|join|sign up|subscribe|contact)\b", re.I)
OUTCOME_WORDS = re.compile(r"\b(report|analysis|audit|results|pricing|demo|call|diagnostic)\b", re.I)

# Hard override regex for action text detection
FORCE_ACTION_TEXT_RE = re.compile(
    r"\b(work with me|view .* (?:services|work|strategy|projects)|request|book|schedule|get|start|try|contact|apply|hire|download|pricing|learn more|see more)\b",
    re.I
)

# Hard override regex for action href detection
FORCE_ACTION_HREF_RE = re.compile(
    r"(mailto:|/contact\b|/book\b|/schedule\b|/pricing\b|/services/[^/]+|#pricing|#contact|#form)",
    re.I
)


def _guess_kind(text: str, href: Optional[str]) -> str:
    if href:
        return "link"
    return "unknown"


def _classify_location(v: Optional[str]) -> str:
    # visual extractor may provide position; keep safe default
    return v or "unknown"


def extract_visual_ctas(raw_visual: dict) -> list[dict]:
    """
    Extract CTAs from visual elements (when DOM CTAs are missing).
    Returns list of synthetic CTA dicts compatible with CTAItem structure.
    """
    elems = (raw_visual or {}).get("elements") or []
    out = []
    for e in elems:
        if e.get("role") in ("primary_cta", "secondary_cta"):
            out.append({
                "text": e.get("text") or "CTA (visual)",
                "href": None,
                "kind": "visual",
                "location": "above_fold",  # Approximate; for now
                "bucket": "action",
                "is_primary_candidate": e.get("role") == "primary_cta",
                "has_action_verb": True,
                "has_outcome_language": False
            })
    return out


def build_signal_report_v1(
    url: str,
    input_type: str,
    features: Dict[str, Any],
    visual: Optional[Dict[str, Any]] = None,
    dom: Optional[Dict[str, Any]] = None,
) -> SignalReportV1:

    visual = visual or {}
    dom = dom or {}

    # Initialize evidence and ctas lists at the start
    ctas: List[CTAItem] = []
    evidence: List[EvidenceItem] = []
    
    # Get raw visual for visual CTA bridge (from visual parameter)
    raw_visual = visual if isinstance(visual, dict) else {}

    # Pull basic signals (prefer visual model output if exists, fallback to DOM)
    hero = (features.get("visual", {}) or {}).get("hero_headline")
    hero = hero or (dom.get("hero_headline") if dom else None)
    
    # Hero fallback from text key_lines
    if not hero:
        key_lines = (features.get("text", {}) or {}).get("key_lines") or []
        ignore = {"home", "about", "services", "ai marketing", "projects", "articles", "research", "seminars", "contact"}
        for line in key_lines:
            if line and line.strip().lower() not in ignore:
                hero = line.strip()
                evidence.append(EvidenceItem(source="text", detail=f"hero_fallback='{hero}'"))
                break
    
    sub = (features.get("visual", {}) or {}).get("subheadline")
    sub = sub or (dom.get("subheadline") if dom else None)

    has_pricing = bool((features.get("visual", {}) or {}).get("has_pricing"))
    has_testimonials = bool((features.get("visual", {}) or {}).get("has_testimonials"))
    has_logos = bool((features.get("visual", {}) or {}).get("has_logos"))
    has_guarantee = bool((features.get("visual", {}) or {}).get("has_guarantee"))

    # CTA extraction (from dom if available; else from visual primary_cta_text)

    dom_ctas = dom.get("ctas") or []  # expect list of {"text","href","location","kind","bucket"}
    for c in dom_ctas:
        text = (c.get("text") or "").strip()
        if not text:
            continue
        href = c.get("href")
        kind = c.get("kind") or _guess_kind(text, href)
        loc = _classify_location(c.get("location"))
        bucket = c.get("bucket") or "content"  # Default to "content" if not provided
        
        # Normalize text and href for matching
        href_norm = (href or "").strip()
        text_norm = (text or "").strip()
        
        # HARD OVERRIDE: text OR href indicates action intent
        if bucket != "nav":
            if FORCE_ACTION_TEXT_RE.search(text_norm) or FORCE_ACTION_HREF_RE.search(href_norm):
                bucket = "action"
                evidence.append(EvidenceItem(source="dom", detail=f"bucket_override text='{text_norm}' href='{href_norm}' -> action"))
        
        has_action = bool(ACTION_VERBS.search(text))
        has_outcome = bool(OUTCOME_WORDS.search(text))
        ctas.append(CTAItem(
            text=text, href=href, kind=kind, location=loc, bucket=bucket,
            has_action_verb=has_action,
            has_outcome_language=has_outcome,
            is_primary_candidate=False
        ))

    # Bridge: Extract CTAs from visual elements if DOM CTAs are empty
    visual_ctas = extract_visual_ctas(raw_visual)
    
    # Bridge only if DOM CTA empty
    if (not ctas) and visual_ctas:
        # Convert visual CTAs to CTAItem format
        for vc in visual_ctas[:3]:  # Limit to 3
            ctas.append(CTAItem(
                text=vc.get("text", "CTA (visual)"),
                href=vc.get("href"),
                kind=vc.get("kind", "visual"),
                location=vc.get("location", "above_fold"),
                bucket=vc.get("bucket", "action"),
                has_action_verb=vc.get("has_action_verb", True),
                has_outcome_language=vc.get("has_outcome_language", False),
                is_primary_candidate=vc.get("is_primary_candidate", False)
            ))
        evidence.append(EvidenceItem(
            source="visual",
            detail=f"cta_bridge_from_visual count={len(visual_ctas[:3])} (DOM had none)"
        ))

    # fallback from visual primary_cta_text if dom is empty
    primary_text = (features.get("visual", {}) or {}).get("primary_cta_text")
    primary_pos = (features.get("visual", {}) or {}).get("primary_cta_position")
    if primary_text and not any(x.text.lower() == primary_text.lower() for x in ctas):
        ctas.append(CTAItem(
            text=str(primary_text).strip(),
            href=None,
            kind="button",
            location=_classify_location(primary_pos or "unknown"),
            bucket="action",  # Visual primary CTA is typically an action
            has_action_verb=bool(ACTION_VERBS.search(primary_text)),
            has_outcome_language=bool(OUTCOME_WORDS.search(primary_text)),
            is_primary_candidate=False  # Will be set by primary selection logic below
        ))
        evidence.append(EvidenceItem(source="visual", detail=f"primary_cta_text={primary_text}"))

    # Separate CTAs by bucket
    action_ctas = [x for x in ctas if x.bucket == "action"]
    nav_ctas = [x for x in ctas if x.bucket == "nav"]
    content_ctas = [x for x in ctas if x.bucket == "content"]

    # Primary selection logic (only from action bucket)
    primary_idx = None

    # 1) above_fold button/submit
    for i, x in enumerate(action_ctas):
        if x.location == "above_fold" and x.kind in ("button", "form_submit") and x.has_action_verb:
            primary_idx = i
            break

    # 2) action verb
    if primary_idx is None:
        for i, x in enumerate(action_ctas):
            if x.has_action_verb:
                primary_idx = i
                break

    # 3) first action
    if primary_idx is None and action_ctas:
        primary_idx = 0

    # Mark primary in the original list
    if primary_idx is not None:
        # Find same object in ctas and mark it
        primary_text = action_ctas[primary_idx].text
        for x in ctas:
            if x.text == primary_text and x.bucket == "action":
                x.is_primary_candidate = True
                break

    # Counts
    cta_count_action = len(action_ctas)
    cta_count_nav = len(nav_ctas)
    cta_count_content = len(content_ctas)
    cta_count_total = len(ctas)

    # Above-fold availability (only for action CTAs)
    known_locs = [x for x in action_ctas if x.location != "unknown"]
    above_fold_available = len(known_locs) > 0
    cta_count_above_fold = None
    if above_fold_available:
        cta_count_above_fold = sum(1 for x in action_ctas if x.location == "above_fold")

    report = SignalReportV1(
        url=url,
        input_type=input_type,
        screenshot_used=bool(visual.get("screenshot_used", False)),
        cta_detected=cta_count_action > 0,  # Only action CTAs count
        primary_cta_detected=primary_idx is not None and cta_count_action > 0,  # Only if action CTAs exist
        cta_count_total=cta_count_total,
        cta_count_action=cta_count_action,
        cta_count_nav=cta_count_nav,
        cta_count_content=cta_count_content,
        cta_count_above_fold=cta_count_above_fold,
        above_fold_available=above_fold_available,
        ctas=ctas,
        has_testimonials=has_testimonials,
        has_logos=has_logos,
        has_pricing=has_pricing,
        has_guarantee=has_guarantee,
        has_contact=True if dom.get("has_contact") else False,
        hero_headline=hero,
        subheadline=sub,
        risk_flags=[],
        evidence=evidence,
        raw={"features": features, "visual": visual, "dom": dom},
    )

    return report

