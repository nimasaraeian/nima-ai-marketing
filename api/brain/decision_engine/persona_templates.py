"""
Persona Templates by Page Type

Provides context-aware mindset personas based on page type and brand context.
Ensures no generic ecommerce/SaaS language leaks into B2B/personal brand contexts.
"""
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def build_personas(page_type: str, brand_context: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Build mindset personas based on page type.
    
    Args:
        page_type: Detected page type
        brand_context: Brand context dict with maturity, etc.
        
    Returns:
        List of 3 personas (hesitant, curious, ready)
    """
    # Personal Brand / Consultant
    if page_type == "personal_brand_consultant":
        return _build_personal_brand_personas()
    
    # B2B Corporate Service
    if page_type == "b2b_corporate_service":
        return _build_b2b_corporate_personas()
    
    # Enterprise B2B
    if page_type == "enterprise_b2b":
        return _build_enterprise_b2b_personas(brand_context)
    
    # Ecommerce
    if page_type.startswith("ecommerce_"):
        return _build_ecommerce_personas()
    
    # SaaS
    if page_type.startswith("saas_"):
        return _build_saas_personas(brand_context)
    
    # Leadgen / Local Service
    if page_type in ["leadgen_landing", "local_service"]:
        return _build_leadgen_personas()
    
    # Default (fallback)
    return _build_default_personas()


def _build_personal_brand_personas() -> List[Dict[str, str]]:
    """Build personas for personal brand/consultant pages."""
    return [
        {
            "id": "hesitant",
            "title": "Hesitant Visitor",
            "signal": "Unclear personal fit and outcome expectations",
            "goal": "Understand if this expert is right for my specific problem",
            "best_cta": "See How I Can Help",
            "next_step": "Clarify scope, outcomes, and engagement style"
        },
        {
            "id": "curious",
            "title": "Curious Evaluator",
            "signal": "Evaluating credibility and thinking alignment",
            "goal": "Validate expertise and approach",
            "best_cta": "View Case Examples",
            "next_step": "Show proof of thinking and past results"
        },
        {
            "id": "ready",
            "title": "Ready to Engage",
            "signal": "Trust established but action path unclear",
            "goal": "Start a low-risk conversation",
            "best_cta": "Book a Call",
            "next_step": "Reduce commitment anxiety (no obligation)"
        }
    ]


def _build_b2b_corporate_personas() -> List[Dict[str, str]]:
    """Build personas for B2B corporate service pages (organizational risk focus)."""
    return [
        {
            "id": "hesitant",
            "title": "Hesitant Decision Maker",
            "signal": "Concern about internal approval and decision risk",
            "goal": "Avoid making a wrong vendor choice",
            "best_cta": "Understand Our Approach",
            "next_step": "Provide clarity for internal justification"
        },
        {
            "id": "curious",
            "title": "Curious Evaluator",
            "signal": "Comparing providers and scope",
            "goal": "Assess fit and capability",
            "best_cta": "View Relevant Projects",
            "next_step": "Highlight differentiation and process"
        },
        {
            "id": "ready",
            "title": "Ready to Move Forward",
            "signal": "Aligned internally but next step unclear",
            "goal": "Move decision forward safely",
            "best_cta": "Contact the Team",
            "next_step": "Make next step explicit and low-friction"
        }
    ]


def _build_enterprise_b2b_personas(brand_context: Dict[str, Any]) -> List[Dict[str, str]]:
    """Build personas for enterprise B2B pages."""
    return [
        {
            "id": "hesitant",
            "title": "First-Time / Non-Expert / Risk-Sensitive Visitor",
            "signal": "First-time or non-expert visitor who needs more context before deciding",
            "goal": "Understand enterprise fit and security requirements",
            "best_cta": "See Security & Compliance",
            "next_step": "Clarify enterprise requirements and security posture"
        },
        {
            "id": "curious",
            "title": "Curious Evaluator",
            "signal": "Evaluating enterprise fit and integration capabilities",
            "goal": "Understand technical requirements and integration path",
            "best_cta": "View Integration Docs",
            "next_step": "Provide technical documentation and integration guides"
        },
        {
            "id": "ready",
            "title": "Informed Buyer Needs Clear Next Step",
            "signal": "Informed buyer ready to act but needs clear next step",
            "goal": "Initiate enterprise sales conversation",
            "best_cta": "Talk to Sales",
            "next_step": "Optimize sales contact flow and reduce friction"
        }
    ]


def _build_ecommerce_personas() -> List[Dict[str, str]]:
    """Build personas for ecommerce pages."""
    return [
        {
            "id": "hesitant",
            "title": "Risk-Sensitive Shopper",
            "signal": "Concerned about returns, shipping, payment security",
            "goal": "Reduce perceived risk before purchase",
            "best_cta": "See Shipping & Returns",
            "next_step": "Add trust badges, clear return policy, secure payment indicators"
        },
        {
            "id": "curious",
            "title": "Comparison-Seeker",
            "signal": "Evaluating product against alternatives",
            "goal": "Compare features, reviews, and specifications",
            "best_cta": "View Reviews & Specs",
            "next_step": "Improve product comparison tools and review visibility"
        },
        {
            "id": "ready",
            "title": "Ready to Purchase",
            "signal": "Ready to buy but needs frictionless checkout",
            "goal": "Complete purchase quickly and securely",
            "best_cta": "Add to Cart",
            "next_step": "Optimize checkout flow, reduce form fields, add express checkout"
        }
    ]


def _build_saas_personas(brand_context: Dict[str, Any]) -> List[Dict[str, str]]:
    """Build personas for SaaS pages."""
    is_enterprise = brand_context.get("brand_maturity") == "enterprise"
    
    if is_enterprise:
        return _build_enterprise_b2b_personas(brand_context)
    
    return [
        {
            "id": "hesitant",
            "title": "Hesitant Visitor",
            "signal": "Uncertain about commitment and value",
            "goal": "Understand value before committing",
            "best_cta": "See Why Users Hesitate",
            "next_step": "Add risk reversal mechanisms (free trial, guarantees)"
        },
        {
            "id": "curious",
            "title": "Curious Evaluator",
            "signal": "Evaluating features and fit",
            "goal": "Compare plans and understand capabilities",
            "best_cta": "Compare Plans",
            "next_step": "Improve feature comparison and plan clarity"
        },
        {
            "id": "ready",
            "title": "Ready to Start",
            "signal": "Ready to try but needs clear signup path",
            "goal": "Start free trial with minimal friction",
            "best_cta": "Start Free Trial",
            "next_step": "Optimize signup flow and reduce form fields"
        }
    ]


def _build_leadgen_personas() -> List[Dict[str, str]]:
    """Build personas for lead generation pages."""
    return [
        {
            "id": "hesitant",
            "title": "Risk-Averse Service Seeker",
            "signal": "Needs credibility and risk reversal before booking",
            "goal": "Verify credibility and reduce commitment risk",
            "best_cta": "See Testimonials",
            "next_step": "Add testimonials, guarantees, and 'no obligation' messaging"
        },
        {
            "id": "curious",
            "title": "Curious Evaluator",
            "signal": "Evaluating service fit and value",
            "goal": "Understand service scope and outcomes",
            "best_cta": "Learn More",
            "next_step": "Clarify service offerings and expected outcomes"
        },
        {
            "id": "ready",
            "title": "Ready to Book",
            "signal": "Ready to book but needs low-friction path",
            "goal": "Schedule consultation with minimal effort",
            "best_cta": "Book a Call",
            "next_step": "Simplify booking form and reduce fields"
        }
    ]


def _build_default_personas() -> List[Dict[str, str]]:
    """Default personas when page type is unknown."""
    return [
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

