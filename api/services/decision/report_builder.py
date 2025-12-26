"""
Canonical report builder for all input types (URL/IMAGE/TEXT).

This is the SINGLE source of truth for building human reports.
All endpoints (url-human, image-human, text-human) must use this function.
"""
import logging
from typing import Dict, Any
from api.schemas.page_map import PageMap

logger = logging.getLogger(__name__)


async def build_human_report_from_page_map(
    page_map: PageMap,
    goal: str,
    locale: str = "en"
) -> Dict[str, Any]:
    """
    Build complete human report from PageMap using the REAL pipeline.
    
    This function uses the exact same pipeline as build_human_decision_review
    and ensures NO template fallbacks are used.
    
    Args:
        page_map: PageMap instance
        goal: Analysis goal
        locale: Locale (default: "en")
        
    Returns:
        Dictionary with:
        - human_report: str (non-empty, length >= 200)
        - summary: dict
        - issues_count: int
        - findings: dict
        - debug: dict
        - (other fields from pipeline)
        
    Raises:
        ValueError: If report generation fails or returns empty/invalid report
    """
    # Use the unified report_from_page_map which uses the full pipeline
    from api.services.decision.report_from_map import report_from_page_map
    
    try:
        report = await report_from_page_map(page_map)
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise ValueError(f"Report generation failed: {str(e)}")
    
    # STRICT VALIDATION: Ensure report is real, not a template
    human_report = report.get("human_report") or report.get("report") or ""
    
    # Validation 1: human_report must exist and be non-empty
    if not human_report or len(human_report.strip()) == 0:
        raise ValueError("Generated report is empty")
    
    # Validation 2: human_report must be at least 200 characters
    if len(human_report.strip()) < 200:
        raise ValueError(f"Generated report is too short ({len(human_report.strip())} chars, minimum 200)")
    
    # Validation 3: Check for fake template markers (exact matches only)
    fake_markers = {
        "headline": "Decision Friction Detected",  # Exact default template headline
        "primary_cta": "See Why Users Hesitate",  # Exact default template CTA
        "secondary_cta": "Learn More"  # Exact default template secondary CTA
    }
    
    # Check decision_psychology_insight - only reject if it's the EXACT default template
    insight = report.get("decision_psychology_insight", {})
    if isinstance(insight, dict):
        headline = insight.get("headline", "")
        # Only reject if it's the exact default template headline AND has the exact default insight text
        if headline == fake_markers["headline"]:
            default_insight_text = "Multiple subtle friction points are creating hesitation. Users are close to deciding but need one clear path forward."
            if insight.get("insight", "") == default_insight_text:
                raise ValueError("Fake template detected: decision_psychology_insight matches exact default template")
    
    # Check CTA recommendations - only reject if it's the EXACT default template
    cta_recs = report.get("cta_recommendations", {})
    if isinstance(cta_recs, dict):
        primary = cta_recs.get("primary", {})
        if isinstance(primary, dict):
            primary_label = primary.get("label", "")
            # Only reject if it's the exact default template CTA AND has the exact default reason
            if primary_label == fake_markers["primary_cta"]:
                default_reason = "Focuses on understanding decision friction"
                if primary.get("reason", "") == default_reason:
                    raise ValueError("Fake template detected: primary CTA matches exact default template")
        
        secondary = cta_recs.get("secondary", [])
        if isinstance(secondary, list):
            for sec in secondary:
                if isinstance(sec, dict):
                    sec_label = sec.get("label", "")
                    # Only reject if it's the exact default template secondary CTA
                    if sec_label == fake_markers["secondary_cta"]:
                        default_sec_reason = "Low-pressure option for users not ready to commit"
                        if sec.get("reason", "") == default_sec_reason:
                            raise ValueError("Fake template detected: secondary CTA matches exact default template")
    
    # Extract required fields
    summary = report.get("summary", {})
    if not isinstance(summary, dict):
        summary = {"message": str(summary) if summary else "Analysis completed."}
    
    findings = report.get("findings", {})
    if not isinstance(findings, dict):
        findings = {}
    
    top_issues = findings.get("top_issues", []) if isinstance(findings, dict) else []
    issues_count = len(top_issues) if isinstance(top_issues, list) else 0
    
    # Return canonical format
    return {
        "human_report": human_report,
        "summary": summary,
        "issues_count": issues_count,
        "findings": findings,
        "debug": report.get("debug", {}),
        # Include other fields from pipeline (but NOT template fields if they're fake)
        "page_type": report.get("page_type"),
        "screenshots": report.get("screenshots"),
        # Only include signature layers if they're real (not templates)
        "decision_psychology_insight": insight if insight.get("headline") != fake_markers["headline"] else None,
        "cta_recommendations": cta_recs if not (isinstance(cta_recs, dict) and cta_recs.get("primary", {}).get("label") == fake_markers["primary_cta"]) else None,
        "cost_of_inaction": report.get("cost_of_inaction"),
        "mindset_personas": report.get("mindset_personas")
    }

