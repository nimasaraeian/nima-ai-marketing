"""
Guardrails to filter invalid recommendations based on page type and detected elements.

Prevents inappropriate suggestions like "consultation CTA" for marketplaces or
"change H1" when no H1 exists.
"""
from typing import Dict, Any, List, Optional
from api.services.page_type_detection import PageType


def filter_invalid_recommendations(
    findings: Dict[str, Any],
    page_type: PageType,
    page_map: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Filter out invalid recommendations based on page type and detected elements.
    
    Args:
        findings: Findings dictionary with issues, quick_wins, copy_suggestions
        page_type: Detected page type
        page_map: Extracted page structure (headlines, CTAs, etc.)
        
    Returns:
        Filtered findings dictionary
    """
    if not isinstance(findings, dict):
        return findings
    
    filtered_findings = findings.copy()
    
    # Extract page elements
    headlines = page_map.get("headlines", []) if isinstance(page_map, dict) else []
    ctas = page_map.get("ctas", []) if isinstance(page_map, dict) else []
    
    # Check if H1 exists
    has_h1 = any(
        isinstance(h, dict) and h.get("tag") == "h1" 
        for h in headlines
    ) if isinstance(headlines, list) else False
    
    # Check CTA count
    cta_count = len(ctas) if isinstance(ctas, list) else 0
    
    # Filter issues
    issues = filtered_findings.get("top_issues", [])
    if isinstance(issues, list):
        filtered_issues = []
        for issue in issues:
            if isinstance(issue, dict):
                issue_id = issue.get("id", "")
                
                # Skip H1-related issues if no H1 exists
                if not has_h1 and issue_id == "clarity_weak_h1":
                    continue
                
                # Skip CTA missing if multiple CTAs exist (for marketplaces)
                if page_type == "ecommerce_marketplace" and issue_id == "cta_missing" and cta_count > 0:
                    continue
                
                # Skip consultation-style CTA suggestions for marketplaces
                if page_type == "ecommerce_marketplace":
                    problem_text = (issue.get("problem", "") or "").lower()
                    fix_steps = issue.get("fix_steps", [])
                    if isinstance(fix_steps, list):
                        fix_text = " ".join(str(s) for s in fix_steps).lower()
                        if "consultation" in problem_text or "consultation" in fix_text:
                            continue
                        if "book a call" in problem_text or "book a call" in fix_text:
                            continue
                        if "request a quote" in problem_text or "request a quote" in fix_text:
                            continue
                
                filtered_issues.append(issue)
        
        filtered_findings["top_issues"] = filtered_issues
    
    # Filter quick wins
    quick_wins = filtered_findings.get("quick_wins", [])
    if isinstance(quick_wins, list):
        filtered_quick_wins = []
        for win in quick_wins:
            if isinstance(win, dict):
                action = (win.get("action", "") or "").lower()
            elif isinstance(win, str):
                action = win.lower()
            else:
                action = ""
            
            # Skip H1-related quick wins if no H1 exists
            if not has_h1 and ("h1" in action or "headline" in action):
                continue
            
            # Skip consultation-style quick wins for marketplaces
            if page_type == "ecommerce_marketplace":
                if any(phrase in action for phrase in [
                    "consultation", "book a call", "request a quote",
                    "book consultation", "get consultation"
                ]):
                    continue
            
            # Skip "missing CTA" if multiple CTAs exist
            if cta_count > 1 and "missing" in action and "cta" in action:
                continue
            
            filtered_quick_wins.append(win)
        
        filtered_findings["quick_wins"] = filtered_quick_wins
    
    # Filter copy suggestions
    copy_suggestions = filtered_findings.get("copy_suggestions", {})
    if isinstance(copy_suggestions, dict):
        filtered_copy = copy_suggestions.copy()
        
        # Filter headline suggestions if no H1 exists
        if not has_h1:
            filtered_copy["headlines"] = []
        elif isinstance(filtered_copy.get("headlines"), list):
            # For marketplaces, remove consultation-style headlines
            if page_type == "ecommerce_marketplace":
                filtered_headlines = []
                for h in filtered_copy["headlines"]:
                    if isinstance(h, dict):
                        text = (h.get("text", "") or "").lower()
                        if not any(phrase in text for phrase in ["consultation", "book", "quote"]):
                            filtered_headlines.append(h)
                filtered_copy["headlines"] = filtered_headlines
        
        # Filter CTA suggestions
        if isinstance(filtered_copy.get("cta_labels"), list):
            filtered_ctas = []
            for cta in filtered_copy["cta_labels"]:
                if isinstance(cta, dict):
                    text = (cta.get("text", "") or "").lower()
                    
                    # For marketplaces, remove consultation CTAs
                    if page_type == "ecommerce_marketplace":
                        if any(phrase in text for phrase in [
                            "consultation", "book a call", "request a quote",
                            "book consultation", "get consultation"
                        ]):
                            continue
                    
                    filtered_ctas.append(cta)
            filtered_copy["cta_labels"] = filtered_ctas
        
        filtered_findings["copy_suggestions"] = filtered_copy
    
    return filtered_findings


def count_forbidden_suggestions(
    findings: Dict[str, Any],
    page_type: PageType,
    page_map: Dict[str, Any]
) -> Dict[str, int]:
    """
    Count how many forbidden suggestions were filtered out.
    
    Returns:
        Dictionary with counts of filtered items by category
    """
    original_issues_count = len(findings.get("top_issues", []))
    original_quick_wins_count = len(findings.get("quick_wins", []))
    original_headlines_count = len(findings.get("copy_suggestions", {}).get("headlines", []))
    original_ctas_count = len(findings.get("copy_suggestions", {}).get("cta_labels", []))
    
    filtered = filter_invalid_recommendations(findings, page_type, page_map)
    
    filtered_issues_count = len(filtered.get("top_issues", []))
    filtered_quick_wins_count = len(filtered.get("quick_wins", []))
    filtered_headlines_count = len(filtered.get("copy_suggestions", {}).get("headlines", []))
    filtered_ctas_count = len(filtered.get("copy_suggestions", {}).get("cta_labels", []))
    
    return {
        "issues_filtered": original_issues_count - filtered_issues_count,
        "quick_wins_filtered": original_quick_wins_count - filtered_quick_wins_count,
        "headlines_filtered": original_headlines_count - filtered_headlines_count,
        "ctas_filtered": original_ctas_count - filtered_ctas_count,
        "total_filtered": (
            (original_issues_count - filtered_issues_count) +
            (original_quick_wins_count - filtered_quick_wins_count) +
            (original_headlines_count - filtered_headlines_count) +
            (original_ctas_count - filtered_ctas_count)
        )
    }









