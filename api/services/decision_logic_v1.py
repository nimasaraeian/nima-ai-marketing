from typing import Dict, Any, List
from api.schemas.signal_v1 import SignalReportV1
from api.schemas.decision_v1 import DecisionLogicV1, DecisionBlocker


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def severity_from_conf(conf: float) -> str:
    if conf >= 0.75:
        return "high"
    if conf >= 0.45:
        return "medium"
    return "low"


def build_decision_logic_v1(signals: SignalReportV1) -> DecisionLogicV1:
    blockers: List[DecisionBlocker] = []

    # ---------- Inputs ----------
    cta_action = signals.cta_count_action
    cta_above = signals.cta_count_above_fold if signals.cta_count_above_fold is not None else None

    has_pricing = signals.has_pricing
    has_testimonials = signals.has_testimonials
    has_logos = signals.has_logos
    has_guarantee = signals.has_guarantee

    hero_ok = bool(signals.hero_headline and len(signals.hero_headline.strip()) >= 8)

    # ---------- Blocker rules ----------
    # B1: missing_pricing
    if not has_pricing:
        conf = 0.85
        blockers.append(DecisionBlocker(
            id="missing_pricing",
            severity="high",
            confidence=conf,
            evidence=["signals.has_pricing=false"],
            metrics={}
        ))

    # B2: weak_trust_signals (testimonials/logos/guarantee absent)
    trust_count = sum([1 if has_testimonials else 0, 1 if has_logos else 0, 1 if has_guarantee else 0])
    if trust_count == 0:
        conf = 0.75
        blockers.append(DecisionBlocker(
            id="weak_trust_signals",
            severity="high",
            confidence=conf,
            evidence=["no_testimonials", "no_logos", "no_guarantee"],
            metrics={"trust_signal_count": trust_count}
        ))
    elif trust_count == 1:
        conf = 0.55
        blockers.append(DecisionBlocker(
            id="weak_trust_signals",
            severity="medium",
            confidence=conf,
            evidence=["only_1_trust_signal_present"],
            metrics={"trust_signal_count": trust_count}
        ))

    # B3: cta_not_detected / cta_below_fold
    if cta_action == 0:
        conf = 0.90
        blockers.append(DecisionBlocker(
            id="cta_not_detected",
            severity="high",
            confidence=conf,
            evidence=["cta_count_action=0"],
            metrics={"cta_count_action": cta_action}
        ))
    else:
        if signals.above_fold_available and (cta_above == 0):
            conf = 0.70
            blockers.append(DecisionBlocker(
                id="cta_below_fold",
                severity="medium",
                confidence=conf,
                evidence=["cta_count_above_fold=0"],
                metrics={"cta_count_action": cta_action, "cta_count_above_fold": cta_above}
            ))

    # B4: missing_hero_headline
    if not hero_ok:
        conf = 0.65
        blockers.append(DecisionBlocker(
            id="missing_hero_headline",
            severity="medium",
            confidence=conf,
            evidence=["hero_headline=null_or_too_short"],
            metrics={"hero_headline": signals.hero_headline}
        ))

    # ---------- Scores ----------
    # weights (simple v1)
    weights = {
        "pricing": 0.30,
        "trust": 0.25,
        "cta": 0.25,
        "clarity": 0.20
    }

    pricing_score = 1.0 if has_pricing else 0.25
    trust_score = {0: 0.25, 1: 0.50, 2: 0.75, 3: 0.90}.get(trust_count, 0.25)
    cta_score = 0.90 if (cta_action > 0 and (cta_above is None or cta_above > 0)) else (0.55 if cta_action > 0 else 0.20)
    clarity_score = 0.75 if hero_ok else 0.40

    decision_probability = (
        pricing_score * weights["pricing"] +
        trust_score * weights["trust"] +
        cta_score * weights["cta"] +
        clarity_score * weights["clarity"]
    )
    decision_probability = clamp(decision_probability)

    # expose component scores
    scores = {
        "pricing": pricing_score,
        "trust": trust_score,
        "cta": cta_score,
        "clarity": clarity_score
    }

    # store transparent inputs
    inputs: Dict[str, Any] = {
        "cta_count_action": cta_action,
        "cta_count_above_fold": cta_above,
        "above_fold_available": signals.above_fold_available,
        "has_pricing": has_pricing,
        "has_testimonials": has_testimonials,
        "has_logos": has_logos,
        "has_guarantee": has_guarantee,
        "hero_headline": signals.hero_headline,
    }

    return DecisionLogicV1(
        url=signals.url,
        blockers=blockers,
        scores=scores,
        decision_probability=decision_probability,
        weights=weights,
        inputs=inputs
    )

