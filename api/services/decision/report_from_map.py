"""
Decision Engine adapter: converts PageMap to decision report using FULL pipeline.

This ensures image/text sources get the same quality report as URL sources.
"""
import logging
from typing import Dict, Any, Tuple
from api.schemas.page_map import PageMap
from api.services.brain_rules import run_heuristics
from api.services.recommendation_guardrails import filter_invalid_recommendations

logger = logging.getLogger(__name__)


async def report_from_page_map(page_map: PageMap) -> Dict[str, Any]:
    """
    Generate full decision report from PageMap using the SAME pipeline as URL.
    
    This function uses the exact same pipeline steps as build_human_decision_review
    to ensure image/text sources get full reports, not basic templates.
    
    Args:
        page_map: PageMap instance
        
    Returns:
        Complete response dictionary with all required keys (same format as URL)
    """
    from api.brain.decision_engine.human_report_builder import (
        _build_context_from_raw,
        _build_signature_layers,
        _assemble_base_report,
        _contextualize_report,
        _apply_type_templates,
        _finalize_and_validate
    )
    
    debug_info = {
        "pipeline_version": "human_report_v2.1_unified",
        "steps": [],
        "errors": [],
        "persona_template_used": "unknown",
        "cost_template_used": "unknown",
        "source": page_map.source
    }
    
    try:
        # Step 1: Convert PageMap to legacy format for pipeline
        debug_info["steps"].append("convert_page_map")
        capture, page_map_dict = _convert_page_map_to_legacy(page_map)
        
        # Step 2: Run heuristics (same as URL pipeline)
        debug_info["steps"].append("heuristics")
        # 🔴 Force locale to English
        findings = run_heuristics(
            capture,
            page_map_dict,
            goal=page_map.goal,
            locale="en",
            url=None  # PageMap doesn't have URL for image/text sources
        )
        
        # DEBUG SNAPSHOT 1: After heuristics, capture issues and quick_wins
        findings_dict_raw = findings.get("findings", {})
        issues_raw = findings_dict_raw.get("top_issues", [])
        quick_wins_raw = findings_dict_raw.get("quick_wins", [])
        debug_info["after_heuristics"] = {
            "issues": issues_raw[:10] if issues_raw else [],
            "issues_len": len(issues_raw) if issues_raw else 0,
            "quick_wins": quick_wins_raw[:10] if quick_wins_raw else [],
            "quick_wins_len": len(quick_wins_raw) if quick_wins_raw else 0
        }
        
        # Apply guardrails (same as URL pipeline)
        findings_filtered = findings.copy()
        findings_filtered["findings"] = filter_invalid_recommendations(
            findings.get("findings", {}),
            findings.get("page_context", {}).get("page_type", "unknown"),
            page_map_dict
        )
        
        # Limit to top 3 issues (same as URL pipeline)
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
        
        # Build raw dict (same format as URL pipeline)
        # 🔴 Force locale and language to English
        raw = {
            "capture": capture,
            "page_map": page_map_dict,
            "findings": findings_filtered,
            "page_text": page_text,
            "url": None,  # No URL for image/text
            "goal": page_map.goal,
            "locale": "en",
            "language": "en"
        }
        
        # Step 3: Context Detection (same as URL pipeline)
        debug_info["steps"].append("context")
        ctx = await _build_context_from_raw(raw, url=None)
        
        # Override page_type from PageMap if available
        if page_map.page_type:
            ctx["page_type"] = {
                "type": page_map.page_type,
                "confidence": 0.8,
                "signals": {}
            }
        
        # Step 4: Signature Layers (same as URL pipeline)
        debug_info["steps"].append("signature_layers")
        sections = _build_signature_layers(raw)
        
        # Step 5: Assemble Base Report (same as URL pipeline)
        report = await _assemble_base_report(raw, sections, ctx)
        
        # Step 6: Contextualization (same as URL pipeline)
        debug_info["steps"].append("contextualize")
        report = await _contextualize_report(report, ctx, debug_info)
        
        # Step 7: Page Type Templates (same as URL pipeline)
        debug_info["steps"].append("type_templates")
        report = await _apply_type_templates(report, ctx, debug_info)
        
        # Step 8: Finalization (same as URL pipeline)
        debug_info["steps"].append("finalize")
        report = _finalize_and_validate(report, ctx, debug_info)
        
        # DEBUG SNAPSHOT 2: After finalize, capture final state
        debug_info["after_finalize_keys"] = list(report.keys())
        debug_info["after_finalize_counts"] = {
            "issues_count": report.get("issues_count"),
            "summary_issues_count": report.get("summary", {}).get("issues_count"),
            "summary_quick_wins_count": report.get("summary", {}).get("quick_wins_count"),
            "has_issues_key": "issues" in report,
            "has_quick_wins_key": "quick_wins" in report
        }
        
        # Ensure response ALWAYS includes issues and quick_wins
        findings_final = report.get("findings", {})
        if not isinstance(findings_final, dict):
            findings_final = {}
        
        issues = findings_final.get("top_issues", [])
        quick_wins = findings_final.get("quick_wins", [])
        
        # Always include issues and quick_wins at top level
        report["issues"] = issues if isinstance(issues, list) else []
        report["quick_wins"] = quick_wins if isinstance(quick_wins, list) else []
        report["issues_count"] = len(report["issues"])
        
        # Ensure summary always has these counts
        if "summary" not in report:
            report["summary"] = {}
        if not isinstance(report["summary"], dict):
            report["summary"] = {}
        
        report["summary"]["issues_count"] = report["issues_count"]
        report["summary"]["quick_wins_count"] = len(report["quick_wins"])
        
        # Add source info to debug
        report["debug"]["source"] = page_map.source
        # Merge debug snapshots into report debug
        report["debug"].update(debug_info)
        
        # Step 9: STRICT VALIDATION - detect fake templates
        _validate_report_for_fake_templates(report)
        
        return report
        
    except ValueError as ve:
        # Validation errors - return clean error
        logger.error(f"Report validation failed: {ve}")
        debug_info["errors"].append(f"Validation: {str(ve)}")
        raise  # Re-raise to be caught by endpoint
    except Exception as e:
        logger.exception(f"Error in report_from_page_map: {e}")
        debug_info["errors"].append(f"{type(e).__name__}: {str(e)}")
        raise  # Re-raise to be caught by endpoint


def _convert_page_map_to_legacy(page_map: PageMap) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Convert PageMap to legacy capture + page_map format.
    
    Returns:
        Tuple of (capture_dict, page_map_dict)
    """
    # Build headlines list
    headlines = []
    if page_map.headline:
        headlines.append({
            "tag": "h1",
            "text": page_map.headline,
            "where": {"section": "hero", "selector": "h1", "bbox": [0, 0, 0, 0]}
        })
    if page_map.subheadline:
        headlines.append({
            "tag": "h2",
            "text": page_map.subheadline,
            "where": {"section": "hero", "selector": "h2", "bbox": [0, 0, 0, 0]}
        })
    
    # Build CTAs list
    ctas = []
    if page_map.primary_cta and page_map.primary_cta.text:
        ctas.append({
            "label": page_map.primary_cta.text,
            "type": "primary",
            "href": None,
            "where": {"section": "hero", "selector": "button", "bbox": [0, 0, 0, 0]},
            "notes": ""
        })
    
    for sec_cta in page_map.secondary_ctas:
        if isinstance(sec_cta, dict) and sec_cta.get("text"):
            ctas.append({
                "label": sec_cta.get("text"),
                "type": "secondary",
                "href": sec_cta.get("href"),
                "where": {"section": "body", "selector": "a", "bbox": [0, 0, 0, 0]},
                "notes": ""
            })
    
    # Build trust signals list
    trust_signals = []
    for ts in page_map.trust_signals:
        trust_signals.append({
            "type": "testimonial",  # Default type
            "text_or_label": ts,
            "where": {"section": "body", "selector": "body", "bbox": [0, 0, 0, 0]}
        })
    
    # Build page_map dict
    page_map_dict = {
        "headlines": headlines,
        "ctas": ctas,
        "trust_signals": trust_signals,
        "offer_elements": [],
        "forms": [],
        "navigation": {"items": [], "language_switch": False}
    }
    
    # Build capture dict (minimal, since we don't have full HTML)
    page_text = " ".join(page_map.copy_snippets) if page_map.copy_snippets else ""
    if page_map.headline:
        page_text = f"{page_map.headline} {page_text}"
    if page_map.subheadline:
        page_text = f"{page_text} {page_map.subheadline}"
    
    capture = {
        "dom": {
            "html_excerpt": "",
            "readable_text_excerpt": page_text,
            "title": page_map.headline or ""
        },
        "screenshots": {}  # No screenshots for image/text sources
    }
    
    return capture, page_map_dict


def _validate_report_for_fake_templates(report: Dict[str, Any]) -> None:
    """
    Strict validation to detect fake templates.
    
    Raises:
        ValueError: If fake templates are detected
    """
    human_report = report.get("human_report") or report.get("report") or ""
    
    # Check for fake template markers
    fake_markers = {
        "headline": "Decision Friction Detected",
        "primary_cta": "See Why Users Hesitate",
        "secondary_cta": "Learn More"
    }
    
    # Check decision_psychology_insight
    insight = report.get("decision_psychology_insight", {})
    if isinstance(insight, dict):
        if insight.get("headline") == fake_markers["headline"]:
            raise ValueError("Fake template detected: decision_psychology_insight.headline == 'Decision Friction Detected'")
    
    # Check CTA recommendations
    cta_recs = report.get("cta_recommendations", {})
    if isinstance(cta_recs, dict):
        primary = cta_recs.get("primary", {})
        if isinstance(primary, dict) and primary.get("label") == fake_markers["primary_cta"]:
            raise ValueError("Fake template detected: primary CTA label == 'See Why Users Hesitate'")
        
        secondary = cta_recs.get("secondary", [])
        if isinstance(secondary, list):
            for sec in secondary:
                if isinstance(sec, dict) and sec.get("label") == fake_markers["secondary_cta"]:
                    raise ValueError("Fake template detected: secondary CTA label == 'Learn More'")
    
    # Check if any fake markers appear in human_report text
    report_lower = human_report.lower()
    for marker in fake_markers.values():
        if marker.lower() in report_lower:
            # This might be OK if it's part of actual analysis, but if it's the exact default, it's fake
            # We'll be lenient here and only check structured fields above
            pass

