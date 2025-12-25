"""
Cost of Inaction Templates by Page Type

Provides context-aware cost of inaction based on page type.
Ensures no generic ecommerce language leaks into B2B/personal brand contexts.
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def build_cost_of_inaction(page_type: str) -> Dict[str, Any]:
    """
    Build cost of inaction based on page type.
    
    Args:
        page_type: Detected page type
        
    Returns:
        Dictionary with headline, bullets (3), and metric_hint
    """
    # Personal Brand / Consultant
    if page_type == "personal_brand_consultant":
        return {
            "headline": "What This Delay Is Costing You",
            "bullets": [
                "Delayed problem resolution due to decision hesitation",
                "Lost momentum while evaluating similar experts",
                "Extended uncertainty about the right strategic direction"
            ],
            "metric_hint": "Track time-to-contact and qualified inquiries"
        }
    
    # B2B Corporate Service
    if page_type == "b2b_corporate_service":
        return {
            "headline": "What This Delay Is Costing the Organization",
            "bullets": [
                "Longer internal decision cycles",
                "Loss of qualified leads during evaluation",
                "Projects postponed due to unclear next steps"
            ],
            "metric_hint": "Track sales cycle length and lead-to-meeting rate"
        }
    
    # Enterprise B2B
    if page_type == "enterprise_b2b":
        return {
            "headline": "What This Delay Is Costing the Organization",
            "bullets": [
                "Extended vendor evaluation cycles",
                "Delayed project implementation",
                "Missed opportunities from unclear decision paths"
            ],
            "metric_hint": "Track RFP-to-decision time and sales cycle length"
        }
    
    # Ecommerce
    if page_type.startswith("ecommerce_"):
        return {
            "headline": "What This Is Costing You",
            "bullets": [
                "Lower conversion rates from unresolved friction",
                "Higher cart abandonment from unclear shipping/returns",
                "Reduced average order value from trust gaps"
            ],
            "metric_hint": "Track conversion rate, cart abandonment rate, and average order value"
        }
    
    # SaaS
    if page_type.startswith("saas_"):
        return {
            "headline": "What This Is Costing You",
            "bullets": [
                "Lower trial-to-paid conversion from unclear value",
                "Delayed signups from pricing ambiguity",
                "Reduced expansion revenue from unclear upgrade path"
            ],
            "metric_hint": "Track trial conversion rate, time-to-signup, and expansion revenue"
        }
    
    # Leadgen / Local Service
    if page_type in ["leadgen_landing", "local_service"]:
        return {
            "headline": "What This Is Costing You",
            "bullets": [
                "Lower lead quality from unclear value proposition",
                "Delayed bookings from booking friction",
                "Lost opportunities from unclear next steps"
            ],
            "metric_hint": "Track lead quality, booking conversion rate, and time-to-contact"
        }
    
    # Default (fallback)
    return {
        "headline": "What This Is Costing You",
        "bullets": [
            "Lower conversion rates from unresolved friction",
            "Wasted traffic from unclear value proposition",
            "Reduced ROI from suboptimal conversion funnel"
        ],
        "metric_hint": "Track conversion rate, time-to-convert, and bounce rate to measure impact"
    }




