"""
Decision Engine adapter: converts PageMap to decision report.
"""
import logging
from typing import Dict, Any, Tuple
from api.schemas.page_map import PageMap
from api.services.brain_rules import run_heuristics
from api.brain.decision_engine.human_report_builder import build_human_decision_review

logger = logging.getLogger(__name__)


async def report_from_page_map(page_map: PageMap) -> Dict[str, Any]:
    """
    Generate decision report from PageMap.
    
    This function adapts PageMap to the existing decision engine pipeline.
    For URL sources, it uses the existing build_human_decision_review.
    For image/text sources, it converts PageMap to a format compatible with
    the decision engine.
    
    Args:
        page_map: PageMap instance
        
    Returns:
        Complete response dictionary with all required keys
    """
    debug_info = {
        "pipeline_version": "human_report_v2.1_unified",
        "steps": [],
        "errors": [],
        "persona_template_used": "unknown",
        "cost_template_used": "unknown",
        "source": page_map.source
    }
    
    try:
        # For URL sources, we can use the existing pipeline if we have a URL
        # For image/text, we need to build a minimal report from PageMap
        
        # Convert PageMap to legacy format for heuristics
        debug_info["steps"].append("convert_page_map")
        capture, page_map_dict = _convert_page_map_to_legacy(page_map)
        
        # Run heuristics
        debug_info["steps"].append("heuristics")
        findings = run_heuristics(
            capture,
            page_map_dict,
            goal=page_map.goal,
            locale=page_map.language or "en",
            url=None  # PageMap doesn't have URL for image/text sources
        )
        
        # Build a minimal report structure
        # For full report generation, we'd need to call the full pipeline
        # For now, we build a basic structure that matches the expected format
        report = {
            "human_report": _build_basic_report_from_map(page_map, findings),
            "summary": _build_summary_from_findings(findings),
            "findings": findings,
            "page_type": {
                "type": page_map.page_type or "unknown",
                "confidence": 0.8,
                "signals": {}
            },
            "debug": debug_info
        }
        
        return report
        
    except Exception as e:
        logger.exception(f"Error in report_from_page_map: {e}")
        debug_info["errors"].append(f"{type(e).__name__}: {str(e)}")
        return _create_fallback_response_from_map(page_map, debug_info)


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


def _build_basic_report_from_map(page_map: PageMap, findings: Dict[str, Any]) -> str:
    """Build a basic human-readable report from PageMap and findings."""
    lines = []
    lines.append("# Decision Analysis Report")
    lines.append("")
    
    if page_map.headline:
        lines.append(f"## Headline\n{page_map.headline}\n")
    
    if page_map.subheadline:
        lines.append(f"## Subheadline\n{page_map.subheadline}\n")
    
    if page_map.primary_cta and page_map.primary_cta.text:
        lines.append(f"## Primary CTA\n{page_map.primary_cta.text}\n")
    
    top_issues = findings.get("top_issues", []) if isinstance(findings, dict) else []
    if top_issues:
        lines.append("## Top Issues")
        for issue in top_issues[:3]:
            if isinstance(issue, dict):
                lines.append(f"- {issue.get('problem', 'Unknown issue')}")
        lines.append("")
    
    return "\n".join(lines)


def _build_summary_from_findings(findings: Dict[str, Any]) -> str:
    """Build summary from findings."""
    top_issues = findings.get("top_issues", []) if isinstance(findings, dict) else []
    if top_issues:
        first_issue = top_issues[0] if isinstance(top_issues, list) else {}
        if isinstance(first_issue, dict):
            return first_issue.get("problem", "Analysis completed.")
    return "Analysis completed. Review the findings above."


def _create_fallback_response_from_map(page_map: PageMap, debug_info: Dict[str, Any]) -> Dict[str, Any]:
    """Create fallback response when report generation fails."""
    return {
        "status": "error",
        "source": page_map.source,
        "goal": page_map.goal,
        "human_report": f"# Analysis Error\n\nFailed to generate report from {page_map.source} source.",
        "summary": "Analysis failed. Please try again.",
        "findings": {
            "top_issues": [],
            "quick_wins": []
        },
        "debug": debug_info
    }

