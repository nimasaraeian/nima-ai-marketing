"""
Human Report Builder - Single Source of Truth for /api/analyze/url-human Response

Enforces correct pipeline ordering:
1. Core Analysis
2. Context Detection (brand, intent, page_type)
3. Signature Layers (insight, CTAs, cost, personas)
4. Contextualization (enterprise reframing)
5. Page Type Templates
6. Finalization & Validation
"""
import logging
from typing import Dict, Any, Optional
from api.services.page_capture import capture_page_artifacts
from api.services.page_extract import extract_page_map
from api.services.brain_rules import run_heuristics
# LEGACY_MODE_ENABLED = False  # Set to True only for backward compatibility
# from api.services.human_report import render_human_report  # DISABLED - uses legacy format
from api.services.recommendation_guardrails import filter_invalid_recommendations

logger = logging.getLogger(__name__)


async def build_human_decision_review(
    url: str,
    goal: str = "other",
    locale: str = "en"
) -> Dict[str, Any]:
    """
    Build complete human decision review with enforced pipeline ordering.
    
    This is the SINGLE entrypoint for all /api/analyze/url-human responses.
    All code paths must use this function.
    
    Args:
        url: URL to analyze
        goal: Conversion goal
        locale: Locale (always en for now)
        
    Returns:
        Complete response dictionary with all required keys
    """
    debug_info = {
        "pipeline_version": "human_report_v2.1",
        "steps": [],
        "errors": [],
        "persona_template_used": "unknown",
        "cost_template_used": "unknown"
    }
    
    try:
        # Step 1: Core Analysis
        debug_info["steps"].append("core_analysis")
        raw = await _run_core_analysis(url, goal, locale)
        
        # Step 2: Context Detection
        debug_info["steps"].append("context")
        ctx = await _build_context_from_raw(raw, url)
        
        # Step 3: Signature Layers (build before report assembly)
        debug_info["steps"].append("signature_layers")
        sections = _build_signature_layers(raw)
        
        # Step 4: Assemble Base Report (uses signature layers for human_report)
        report = await _assemble_base_report(raw, sections, ctx)
        
        # Step 5: Contextualization
        debug_info["steps"].append("contextualize")
        report = await _contextualize_report(report, ctx, debug_info)
        
        # Step 6: Page Type Templates
        debug_info["steps"].append("type_templates")
        report = await _apply_type_templates(report, ctx, debug_info)
        
        # Step 7: Finalization
        debug_info["steps"].append("finalize")
        report = _finalize_and_validate(report, ctx, debug_info)
        
        return report
        
    except Exception as e:
        logger.exception(f"Error in build_human_decision_review for {url}: {e}")
        debug_info["errors"].append(f"{type(e).__name__}: {str(e)}")
        # Return safe defaults even on error
        return _create_fallback_response(url, goal, locale, debug_info)


async def _run_core_analysis(url: str, goal: str, locale: str) -> Dict[str, Any]:
    """Run core analysis: capture, extract, heuristics."""
    # Capture page artifacts
    capture = await capture_page_artifacts(url)
    
    # Extract page structure
    page_map = extract_page_map(capture)
    
    # Run heuristics
    findings = run_heuristics(
        capture,
        page_map,
        goal=goal,
        locale=locale,
        url=url
    )
    
    # Apply guardrails
    findings_filtered = findings.copy()
    findings_filtered["findings"] = filter_invalid_recommendations(
        findings.get("findings", {}),
        findings.get("page_context", {}).get("page_type", "unknown"),
        page_map
    )
    
    # Limit to top 3 issues
    findings_dict = findings_filtered.get("findings", {})
    top_issues = findings_dict.get("top_issues", [])
    if isinstance(top_issues, list) and len(top_issues) > 3:
        def get_sort_key(issue: Dict[str, Any]) -> float:
            if not isinstance(issue, dict):
                return 0.0
            if "impact_score" in issue:
                return float(issue.get("impact_score", 0.0))
            if "final_severity_score" in issue:
                return float(issue.get("final_severity_score", 0.0))
            severity_map = {"high": 3.0, "medium": 2.0, "low": 1.0}
            severity = str(issue.get("severity", "medium")).lower()
            return severity_map.get(severity, 2.0)
        
        top_issues_sorted = sorted(top_issues, key=get_sort_key, reverse=True)
        findings_dict["top_issues"] = top_issues_sorted[:3]
        findings_filtered["findings"] = findings_dict
    
    # Extract page text
    page_text = ""
    if capture and capture.get("dom"):
        page_text = capture.get("dom", {}).get("readable_text_excerpt", "") or capture.get("dom", {}).get("html_excerpt", "")
    
    return {
        "capture": capture,
        "page_map": page_map,
        "findings": findings_filtered,
        "page_text": page_text,
        "url": url,
        "goal": goal,
        "locale": locale
    }


async def _build_context_from_raw(raw: Dict[str, Any], url: str) -> Dict[str, Any]:
    """Build context (brand, intent, page_type) from raw analysis."""
    try:
        from api.brain.context.brand_context import build_context
        
        page_text = raw.get("page_text", "")
        page_map = raw.get("page_map")
        
        ctx = build_context(url, page_text, page_map)
        return ctx
    except Exception as e:
        logger.warning(f"Failed to build context: {e}")
        # Return default context
        return {
            "brand_context": {
                "brand_maturity": "growth",
                "confidence": 0.5,
                "analysis_mode": "standard"
            },
            "page_intent": {
                "intent": "unknown",
                "confidence": 0.5
            },
            "page_type": {
                "type": "unknown",
                "confidence": 0.0
            }
        }


def _build_signature_layers(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Build signature layers (insight, CTAs, cost, personas) from raw analysis."""
    try:
        from api.brain.decision_engine.enhancers import build_signature_layers
        
        # Convert raw to format expected by enhancers
        findings = raw.get("findings", {})
        report_dict = {
            "findings": findings.get("findings", {}),
            "human_report": "",  # Will be built from signature layers
            "page_type": findings.get("page_context", {}).get("page_type", "unknown"),
            "summary": {"goal": raw.get("goal", "other")}
        }
        
        layers = build_signature_layers(report_dict)
        return layers
    except Exception as e:
        logger.warning(f"Failed to build signature layers: {e}")
        # Return defaults
        return _get_default_signature_layers()


def _build_human_report_from_signature_layers(sections: Dict[str, Any], findings: Dict[str, Any]) -> str:
    """
    Build human report from signature layers (v2 format - no legacy numbered issues).
    
    This replaces the legacy render_human_report() which generates numbered issues.
    """
    lines = []
    
    # Verdict section (from decision_psychology_insight)
    insight = sections.get("decision_psychology_insight", {})
    lines.append("## Verdict")
    lines.append("")
    verdict_text = insight.get("insight", "Multiple subtle friction points are creating hesitation.")
    lines.append(verdict_text)
    lines.append("")
    
    # Why Now section
    lines.append("## Why This Matters Now")
    lines.append("")
    why_now = insight.get("why_now", "Small frictions compound. Addressing the primary blocker unlocks the decision pathway.")
    lines.append(why_now)
    lines.append("")
    
    # Quick Action section (from micro_risk_reducer)
    lines.append("## Quick Action")
    lines.append("")
    action = insight.get("micro_risk_reducer", "Focus on the top blocker identified in the analysis.")
    lines.append(action)
    lines.append("")
    
    # Note: We do NOT include:
    # - Numbered issues (1., 2., 3.) - use structured findings.top_issues instead
    # - Suggested H1 - use structured CTA recommendations instead
    # - Suggested Primary CTA - use structured cta_recommendations instead
    
    return "\n".join(lines)


def _get_default_signature_layers() -> Dict[str, Any]:
    """Return default signature layers when analysis fails."""
    return {
        "decision_psychology_insight": {
            "headline": "Decision Friction Detected",
            "insight": "Multiple subtle friction points are creating hesitation. Users are close to deciding but need one clear path forward.",
            "why_now": "Small frictions compound. Addressing the primary blocker unlocks the decision pathway.",
            "micro_risk_reducer": "Focus on the top blocker identified in the analysis. One clear fix will unlock the decision."
        },
        "cta_recommendations": {
            "primary": {
                "label": "See Why Users Hesitate",
                "reason": "Focuses on understanding decision friction"
            },
            "secondary": [
                {"label": "Learn More", "reason": "Low-pressure option for users not ready to commit"}
            ],
            "do_not_use": [
                {"label": "Click Here", "reason": "Generic and provides no value signal or friction reduction"}
            ]
        },
        "cost_of_inaction": {
            "headline": "What This Is Costing You",
            "bullets": [
                "Lower conversion rates from unresolved friction",
                "Wasted traffic from unclear value proposition",
                "Reduced ROI from suboptimal conversion funnel"
            ],
            "metric_hint": "Track conversion rate, time-to-convert, and bounce rate to measure impact"
        },
        "mindset_personas": [
            {
                "id": "hesitant",
                "title": "Hesitant Visitor",
                "signal": "Risk perception outweighs reward signals",
                "goal": "Build safety and reduce perceived risk",
                "best_cta": "See Why Users Hesitate",
                "next_step": "Add risk reversal mechanisms (guarantees, low-commitment options)"
            },
            {
                "id": "curious",
                "title": "Curious Evaluator",
                "signal": "Clarity/value dominant - evaluating fit and value",
                "goal": "Understand what this is and if it's for them",
                "best_cta": "Understand Your Options",
                "next_step": "Improve value proposition clarity in hero section"
            },
            {
                "id": "ready",
                "title": "Ready-to-Act Buyer",
                "signal": "CTA/flow/effort dominant - ready to act but needs clear path",
                "goal": "Clear, friction-free path to action",
                "best_cta": "Get Started",
                "next_step": "Optimize CTA placement and reduce friction in conversion flow"
            }
        ]
    }


async def _assemble_base_report(raw: Dict[str, Any], sections: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble base report with all required keys."""
    capture = raw.get("capture", {})
    findings = raw.get("findings", {})
    
    # Build analysis JSON for LLM
    capture_for_llm = {}
    if capture:
        capture_for_llm = {
            "timestamp_utc": capture.get("timestamp_utc"),
            "dom": capture.get("dom", {}),
            "screenshots": {
                "desktop": {
                    "viewport": capture.get("screenshots", {}).get("desktop", {}).get("viewport", {}),
                    "screenshot_available": bool(capture.get("screenshots", {}).get("desktop", {}).get("above_the_fold_data_url"))
                },
                "mobile": {
                    "viewport": capture.get("screenshots", {}).get("mobile", {}).get("viewport", {}),
                    "screenshot_available": bool(capture.get("screenshots", {}).get("mobile", {}).get("above_the_fold_data_url"))
                }
            }
        }
    
    analysis_json = {
        "schema_version": "1.0",
        "input": {
            "url": raw.get("url"),
            "goal": raw.get("goal"),
            "locale": raw.get("locale")
        },
        "page_context": findings.get("page_context", {}),
        "capture": capture_for_llm,
        "page_map": raw.get("page_map"),
        "findings": findings.get("findings", {}),
        "output_policy": {
            "no_scores": True,
            "no_percentages": True,
            "tone": "direct_human",
            "max_main_issues": 3
        },
    }
    
    # Generate human report from signature layers (v2 format - no legacy numbered issues)
    # DO NOT use render_human_report() which generates legacy format
    human_report = _build_human_report_from_signature_layers(sections, findings.get("findings", {}))
    
    # Build screenshots response
    screenshots_response = _build_screenshots_response(capture)
    
    # Extract additional data
    page_map = raw.get("page_map", {})
    page_context = findings.get("page_context", {})
    page_type_name = page_context.get("page_type", "unknown")
    analysis_scope = findings.get("analysis_scope", "ruleset:unknown")
    top_issues = findings.get("findings", {}).get("top_issues", [])
    actual_issues_count = len(top_issues) if isinstance(top_issues, list) else 0
    
    # Build summary
    summary = findings.get("summary", {})
    if not summary:
        summary = {
            "url": raw.get("url", ""),
            "goal": raw.get("goal", "other"),
            "locale": raw.get("locale", "en"),
            "headlines_count": len(page_map.get("headlines", [])),
            "ctas_count": len(page_map.get("ctas", [])),
            "issues_count": actual_issues_count,
            "quick_wins_count": len(findings.get("findings", {}).get("quick_wins", [])),
        }
    
    # Assemble base report
    report = {
        "analysisStatus": "ok",
        "human_report": human_report,
        "findings": findings.get("findings", {}),
        "summary": summary,
        "page_type": page_type_name,  # Legacy field (string)
        "analysis_scope": analysis_scope,
        "screenshots": screenshots_response,
        "capture_info": {
            "timestamp": capture.get("timestamp_utc") if capture else None,
            "screenshots": screenshots_response,
            "title": capture.get("dom", {}).get("title") if capture else None,
        },
        "capture": capture if capture else {
            "timestamp_utc": None,
            "screenshots": screenshots_response,
            "dom": {}
        },
        "page_map": {
            "headlines": page_map.get("headlines", []),
            "ctas": page_map.get("ctas", []),
            "trust_signals": page_map.get("trust_signals", []),
        },
        # Context (new structured fields)
        "brand_context": ctx.get("brand_context", {}),
        "page_intent": ctx.get("page_intent", {}),
        "page_type": ctx.get("page_type", {}),  # New structured field
        # Signature layers (will be populated later)
        "decision_psychology_insight": sections.get("decision_psychology_insight", _get_default_signature_layers()["decision_psychology_insight"]),
        "cta_recommendations": sections.get("cta_recommendations", _get_default_signature_layers()["cta_recommendations"]),
        "cost_of_inaction": sections.get("cost_of_inaction", _get_default_signature_layers()["cost_of_inaction"]),
        "mindset_personas": sections.get("mindset_personas", _get_default_signature_layers()["mindset_personas"])
    }
    
    return report


def _build_screenshots_response(capture: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build screenshots response from capture."""
    if not capture:
        return {
            "desktop": {
                "above_the_fold_data_url": None,
                "full_page_data_url": None,
                "viewport": {"width": 1365, "height": 768},
                "above_the_fold": None,
                "aboveFold": None,
                "full_page": None,
            },
            "mobile": {
                "above_the_fold_data_url": None,
                "full_page_data_url": None,
                "viewport": {"width": 390, "height": 844},
                "above_the_fold": None,
                "aboveFold": None,
                "full_page": None,
            }
        }
    
    screenshots_raw = capture.get("screenshots", {})
    desktop_screenshots = screenshots_raw.get("desktop", {})
    mobile_screenshots = screenshots_raw.get("mobile", {})
    
    desktop_atf_data_url = desktop_screenshots.get("above_the_fold_data_url")
    desktop_full_data_url = desktop_screenshots.get("full_page_data_url")
    mobile_atf_data_url = mobile_screenshots.get("above_the_fold_data_url")
    mobile_full_data_url = mobile_screenshots.get("full_page_data_url")
    
    return {
        "desktop": {
            "above_the_fold_data_url": desktop_atf_data_url,
            "full_page_data_url": desktop_full_data_url,
            "viewport": desktop_screenshots.get("viewport", {"width": 1365, "height": 768}),
            "above_the_fold": desktop_atf_data_url,  # Legacy
            "aboveFold": desktop_atf_data_url,  # Legacy
            "full_page": desktop_full_data_url,
        },
        "mobile": {
            "above_the_fold_data_url": mobile_atf_data_url,
            "full_page_data_url": mobile_full_data_url,
            "viewport": mobile_screenshots.get("viewport", {"width": 390, "height": 844}),
            "above_the_fold": mobile_atf_data_url,  # Legacy
            "aboveFold": mobile_atf_data_url,  # Legacy
            "full_page": mobile_full_data_url,
        }
    }


async def _contextualize_report(report: Dict[str, Any], ctx: Dict[str, Any], debug_info: Dict[str, Any]) -> Dict[str, Any]:
    """Apply contextualization (enterprise reframing)."""
    try:
        from api.brain.decision_engine.contextualizer import contextualize_verdict
        return contextualize_verdict(report, ctx)
    except Exception as e:
        logger.warning(f"Failed to contextualize report: {e}")
        debug_info["errors"].append(f"contextualize: {type(e).__name__}")
        return report  # Return unchanged on error


async def _apply_type_templates(report: Dict[str, Any], ctx: Dict[str, Any], debug_info: Dict[str, Any]) -> Dict[str, Any]:
    """Apply page-type-specific templates (personas, cost of inaction)."""
    try:
        from api.brain.decision_engine.templates_by_type import apply_page_type_templates
        from api.brain.decision_engine.persona_templates import build_personas
        from api.brain.decision_engine.cost_templates import build_cost_of_inaction
        
        # Get page type
        page_type = ctx.get("page_type", {})
        page_type_name = page_type.get("type", "unknown")
        brand_context = ctx.get("brand_context", {})
        
        # Replace personas with page-type-specific templates
        try:
            personas = build_personas(page_type_name, brand_context)
            report["mindset_personas"] = personas
            debug_info["persona_template_used"] = page_type_name
        except Exception as e:
            logger.warning(f"Failed to build personas: {e}")
            debug_info["errors"].append(f"persona_templates: {type(e).__name__}")
        
        # Replace cost of inaction with page-type-specific templates
        try:
            cost = build_cost_of_inaction(page_type_name)
            report["cost_of_inaction"] = cost
            debug_info["cost_template_used"] = page_type_name
        except Exception as e:
            logger.warning(f"Failed to build cost of inaction: {e}")
            debug_info["errors"].append(f"cost_templates: {type(e).__name__}")
        
        # Apply other type-specific templates (CTAs, etc.)
        report = apply_page_type_templates(report, ctx)
        
        return report
    except Exception as e:
        logger.warning(f"Failed to apply type templates: {e}")
        debug_info["errors"].append(f"type_templates: {type(e).__name__}")
        return report  # Return unchanged on error


def _finalize_and_validate(report: Dict[str, Any], ctx: Dict[str, Any], debug_info: Dict[str, Any]) -> Dict[str, Any]:
    """Finalize and validate report, add debug info."""
    # Ensure all required keys exist
    required_keys = [
        "brand_context",
        "page_intent",
        "page_type",
        "decision_psychology_insight",
        "cta_recommendations",
        "cost_of_inaction",
        "mindset_personas"
    ]
    
    for key in required_keys:
        if key not in report:
            logger.warning(f"Missing required key: {key}, adding default")
            if key == "decision_psychology_insight":
                report[key] = _get_default_signature_layers()["decision_psychology_insight"]
            elif key == "cta_recommendations":
                report[key] = _get_default_signature_layers()["cta_recommendations"]
            elif key == "cost_of_inaction":
                report[key] = _get_default_signature_layers()["cost_of_inaction"]
            elif key == "mindset_personas":
                report[key] = _get_default_signature_layers()["mindset_personas"]
            else:
                report[key] = ctx.get(key, {})
    
    # Validate human_report does NOT contain legacy phrases
    human_report = report.get("human_report", "")
    legacy_phrases = [
        "lacks trust signals",
        "untrustworthy",
        "suggested h1",
        "suggested primary cta",
        "1.",
        "2.",
        "3."
    ]
    
    found_legacy = []
    human_report_lower = human_report.lower()
    for phrase in legacy_phrases:
        if phrase in human_report_lower:
            found_legacy.append(phrase)
    
    if found_legacy:
        logger.warning(f"Legacy phrases detected in human_report: {found_legacy}")
        debug_info["errors"].append(f"Legacy phrases detected: {', '.join(found_legacy)}")
        # Sanitize the report
        for phrase in found_legacy:
            if phrase in ["1.", "2.", "3."]:
                # Remove numbered issue lists
                import re
                report["human_report"] = re.sub(r'^\d+\.\s+\*\*.*$', '', report["human_report"], flags=re.MULTILINE)
    
    # Safety guards: Check for ecommerce phrases in B2B/personal brand contexts
    page_type_name = ctx.get("page_type", {}).get("type", "unknown")
    if page_type_name.startswith("personal_") or page_type_name.startswith("b2b_"):
        forbidden_phrases = ["add to cart", "buy now", "checkout", "untrustworthy"]
        found_forbidden = []
        
        # Check human_report
        human_report_lower = report.get("human_report", "").lower()
        for phrase in forbidden_phrases:
            if phrase in human_report_lower:
                found_forbidden.append(phrase)
        
        # Check personas
        personas = report.get("mindset_personas", [])
        for persona in personas:
            persona_text = " ".join([
                persona.get("signal", ""),
                persona.get("goal", ""),
                persona.get("best_cta", ""),
                persona.get("next_step", "")
            ]).lower()
            for phrase in forbidden_phrases:
                if phrase in persona_text and phrase not in found_forbidden:
                    found_forbidden.append(phrase)
        
        # Check cost of inaction
        cost_text = " ".join([
            report.get("cost_of_inaction", {}).get("headline", ""),
            " ".join(report.get("cost_of_inaction", {}).get("bullets", []))
        ]).lower()
        for phrase in forbidden_phrases:
            if phrase in cost_text and phrase not in found_forbidden:
                found_forbidden.append(phrase)
        
        if found_forbidden:
            logger.warning(f"Forbidden ecommerce phrases found in {page_type_name} context: {found_forbidden}")
            debug_info["errors"].append(f"Forbidden phrases in {page_type_name}: {', '.join(found_forbidden)}")
            
            # Sanitize: Replace with neutral B2B language
            from api.brain.decision_engine.contextualizer import sanitize_text
            if "untrustworthy" in found_forbidden:
                report["human_report"] = sanitize_text(report.get("human_report", ""))
    
    # Add debug info
    report["debug"] = {
        "pipeline_version": "human_report_v2.1",
        "source": "human_report_v2_only",  # Assertion: confirms v2 pipeline
        "steps": debug_info["steps"],
        "analysis_mode": ctx.get("brand_context", {}).get("analysis_mode", "standard"),
        "brand_maturity": ctx.get("brand_context", {}).get("brand_maturity", "unknown"),
        "page_intent": ctx.get("page_intent", {}).get("intent", "unknown"),
        "page_type": ctx.get("page_type", {}).get("type", "unknown"),
        "persona_template_used": debug_info.get("persona_template_used", "unknown"),
        "cost_template_used": debug_info.get("cost_template_used", "unknown"),
        "errors": debug_info["errors"]
    }
    
    # Remove legacy fields if present
    legacy_fields = ["suggested_h1", "suggested_primary_cta"]
    for field in legacy_fields:
        if field in report:
            logger.warning(f"Removing legacy field: {field}")
            del report[field]
    
    return report


def _create_fallback_response(url: str, goal: str, locale: str, debug_info: Dict[str, Any]) -> Dict[str, Any]:
    """Create fallback response when pipeline fails."""
    default_sections = _get_default_signature_layers()
    default_ctx = {
        "brand_context": {"brand_maturity": "growth", "confidence": 0.5, "analysis_mode": "standard"},
        "page_intent": {"intent": "unknown", "confidence": 0.5},
        "page_type": {"type": "unknown", "confidence": 0.0}
    }
    
    return {
        "analysisStatus": "error",
        "human_report": "Analysis encountered an error. Please try again.",
        "findings": {"top_issues": []},
        "summary": {"goal": goal},
        "page_type": "unknown",
        "screenshots": {
            "desktop": {"above_the_fold_data_url": None, "full_page_data_url": None, "viewport": {"width": 1365, "height": 768}},
            "mobile": {"above_the_fold_data_url": None, "full_page_data_url": None, "viewport": {"width": 390, "height": 844}}
        },
        "brand_context": default_ctx["brand_context"],
        "page_intent": default_ctx["page_intent"],
        "page_type": default_ctx["page_type"],
        "decision_psychology_insight": default_sections["decision_psychology_insight"],
        "cta_recommendations": default_sections["cta_recommendations"],
        "cost_of_inaction": default_sections["cost_of_inaction"],
        "mindset_personas": default_sections["mindset_personas"],
        "debug": {
            "pipeline_version": debug_info["pipeline_version"],
            "steps": debug_info["steps"],
            "analysis_mode": "standard",
            "brand_maturity": "unknown",
            "page_intent": "unknown",
            "page_type": "unknown",
            "errors": debug_info["errors"]
        }
    }

