"""
Shared report builder for URL/IMAGE/TEXT sources.

This ensures all sources use the same full report generation pipeline.
"""
import logging
from typing import Dict, Any
from api.schemas.page_map import PageMap
from api.brain.decision_engine.human_report_builder import build_human_decision_review

logger = logging.getLogger(__name__)


async def build_full_human_report(page_map: PageMap, goal: str) -> Dict[str, Any]:
    """
    Build full human report using the same pipeline as URL analysis.
    
    This function ensures image/text sources get the same quality report as URL.
    
    Args:
        page_map: PageMap instance
        goal: Analysis goal
        
    Returns:
        Complete report dict with human_report, summary, findings, etc.
    """
    # For URL sources, we can use build_human_decision_review directly
    # For image/text, we need to convert PageMap to a format that works with the pipeline
    
    if page_map.source == "url":
        # This shouldn't be called for URL sources (they use build_human_decision_review directly)
        # But if it is, we'd need the URL to call build_human_decision_review
        raise ValueError("build_full_human_report should not be called for URL sources. Use build_human_decision_review directly.")
    
    # For image/text, we need to use the unified pipeline
    # The report_from_page_map function should be updated to use the full pipeline
    from api.services.decision.report_from_map import report_from_page_map
    
    report = await report_from_page_map(page_map)
    
    # Validate report structure
    _validate_report_structure(report, page_map.source)
    
    return report


def _validate_report_structure(report: Dict[str, Any], source: str) -> None:
    """
    Validate report structure and detect fake templates.
    
    Raises:
        ValueError: If report is invalid or contains fake templates
    """
    # Check for error status - should not contain report content
    if report.get("status") == "error":
        human_report = report.get("human_report") or report.get("report") or ""
        if human_report and len(human_report.strip()) > 0:
            # Error responses should not contain report content
            raise ValueError("Error response contains report content")
        return  # Error responses are OK if they don't have report content
    
    # Check for required fields when status is ok
    human_report = report.get("human_report") or report.get("report") or ""
    
    # Validation 1: human_report must exist and be non-empty
    if not human_report or len(human_report.strip()) == 0:
        raise ValueError("human_report is missing or empty")
    
    # Validation 2: human_report must be at least 200 characters
    if len(human_report.strip()) < 200:
        raise ValueError(f"human_report is too short ({len(human_report.strip())} chars, minimum 200)")
    
    # Validation 3: Check for fake template markers
    fake_markers = [
        "Decision Friction Detected",  # Default headline
        "See Why Users Hesitate",  # Default primary CTA
        "Learn More",  # Default secondary CTA
    ]
    
    report_lower = human_report.lower()
    for marker in fake_markers:
        if marker.lower() in report_lower:
            # Check if this is in a structured field (which is OK) vs in the report text
            # If it's in decision_psychology_insight.headline, that's a fake template
            insight = report.get("decision_psychology_insight", {})
            if isinstance(insight, dict):
                if insight.get("headline") == marker:
                    raise ValueError(f"Fake template detected: headline='{marker}'")
            
            # Check CTA recommendations
            cta_recs = report.get("cta_recommendations", {})
            if isinstance(cta_recs, dict):
                primary = cta_recs.get("primary", {})
                if isinstance(primary, dict) and primary.get("label") == marker:
                    raise ValueError(f"Fake template detected: primary CTA='{marker}'")
                secondary = cta_recs.get("secondary", [])
                if isinstance(secondary, list):
                    for sec in secondary:
                        if isinstance(sec, dict) and sec.get("label") == marker:
                            raise ValueError(f"Fake template detected: secondary CTA='{marker}'")
    
    # Validation 4: Check for fake content without corresponding data
    if "CTA Recommendations" in human_report and "cta_recommendations" not in report:
        logger.warning("Report mentions CTA Recommendations but no cta_recommendations field")
    
    if "Personas" in human_report and "mindset_personas" not in report:
        logger.warning("Report mentions Personas but no mindset_personas field")
    
    # Validation 5: Ensure summary exists
    summary = report.get("summary")
    if not summary:
        raise ValueError("summary is missing")
    
    # Validation 6: Ensure findings exist
    findings = report.get("findings", {})
    if not isinstance(findings, dict):
        raise ValueError("findings is missing or invalid")



