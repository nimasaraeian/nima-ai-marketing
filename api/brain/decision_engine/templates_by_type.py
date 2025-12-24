"""
Page Type Templates - Context-aware recommendations by page type

Applies page-type-specific templates to recommendations, CTAs, and personas
to make them contextually appropriate for different business models.
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def apply_page_type_templates(response: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply page-type-specific templates to response.
    
    Args:
        response: Response payload with recommendations, CTAs, personas, etc.
        ctx: Context dict with page_type, brand_context, page_intent
        
    Returns:
        Modified response with page-type-specific templates applied
    """
    page_type = ctx.get("page_type", {})
    page_type_name = page_type.get("type", "unknown")
    
    # Only apply templates if page type is known
    if page_type_name == "unknown":
        return response
    
    # Apply templates based on page type
    if page_type_name == "ecommerce_product":
        response = _apply_ecommerce_product_templates(response, ctx)
    elif page_type_name == "ecommerce_collection":
        response = _apply_ecommerce_collection_templates(response, ctx)
    elif page_type_name == "ecommerce_checkout":
        response = _apply_ecommerce_checkout_templates(response, ctx)
    elif page_type_name == "saas_pricing":
        response = _apply_saas_pricing_templates(response, ctx)
    elif page_type_name in ["leadgen_landing", "local_service"]:
        response = _apply_leadgen_templates(response, ctx)
    elif page_type_name == "enterprise_b2b":
        response = _apply_enterprise_b2b_templates(response, ctx)
    elif page_type_name == "content_blog":
        response = _apply_content_blog_templates(response, ctx)
    elif page_type_name == "saas_home":
        response = _apply_saas_home_templates(response, ctx)
    
    return response


def _apply_ecommerce_product_templates(response: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Apply ecommerce product page templates."""
    # Update CTA recommendations to be transactional
    if "cta_recommendations" in response:
        cta_rec = response["cta_recommendations"]
        
        # Primary CTA should be transactional
        transactional_ctas = [
            {"label": "Add to Cart", "reason": "Direct transactional action for product pages"},
            {"label": "Buy Now", "reason": "Immediate purchase action for ready buyers"},
            {"label": "Choose Size & Add to Cart", "reason": "Guides through product selection"}
        ]
        
        primary = cta_rec.get("primary", {})
        primary_label = primary.get("label", "").lower()
        
        # Replace if not transactional
        if not any(txn in primary_label for txn in ["add to cart", "buy now", "purchase", "checkout"]):
            cta_rec["primary"] = transactional_ctas[0]
        
        # Update secondary CTAs
        cta_rec["secondary"] = [
            {"label": "View Reviews", "reason": "Builds trust through social proof"},
            {"label": "See Shipping Options", "reason": "Reduces shipping anxiety"}
        ]
        
        # Update do_not_use
        cta_rec["do_not_use"] = [
            {"label": "Learn More", "reason": "Too generic for transactional product pages"},
            {"label": "Get Started", "reason": "Not appropriate for ecommerce product pages"}
        ]
    
    # Update personas for ecommerce
    if "mindset_personas" in response:
        personas = response["mindset_personas"]
        for persona in personas:
            if persona.get("id") == "hesitant":
                persona["title"] = "Risk-Sensitive Shopper"
                persona["signal"] = "Concerned about returns, shipping, payment security"
                persona["goal"] = "Reduce perceived risk before purchase"
                persona["best_cta"] = "See Shipping & Returns"
                persona["next_step"] = "Add trust badges, clear return policy, secure payment indicators"
            elif persona.get("id") == "curious":
                persona["title"] = "Comparison-Seeker"
                persona["signal"] = "Evaluating product against alternatives"
                persona["goal"] = "Compare features, reviews, and specifications"
                persona["best_cta"] = "View Reviews & Specs"
                persona["next_step"] = "Improve product comparison tools and review visibility"
            elif persona.get("id") == "ready":
                persona["title"] = "Ready to Purchase"
                persona["signal"] = "Ready to buy but needs frictionless checkout"
                persona["goal"] = "Complete purchase quickly and securely"
                persona["best_cta"] = "Add to Cart"
                persona["next_step"] = "Optimize checkout flow, reduce form fields, add express checkout"
    
    # Update decision psychology insight
    if "decision_psychology_insight" in response:
        insight = response["decision_psychology_insight"]
        insight["headline"] = "Product Clarity and Trust Drive Purchase"
        insight["insight"] = "Ecommerce product pages need clear shipping/returns information, price anchoring, trust badges, and reviews to convert. Delivery time and payment options also impact conversion."
        insight["why_now"] = "Online shoppers need immediate clarity on shipping, returns, and payment to overcome purchase hesitation."
        insight["micro_risk_reducer"] = "Add shipping/returns info above the fold, display trust badges, and make reviews easily accessible."
    
    return response


def _apply_ecommerce_collection_templates(response: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Apply ecommerce collection page templates."""
    if "cta_recommendations" in response:
        cta_rec = response["cta_recommendations"]
        cta_rec["primary"] = {
            "label": "Browse Products",
            "reason": "Collection pages focus on product discovery"
        }
    
    return response


def _apply_ecommerce_checkout_templates(response: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Apply ecommerce checkout page templates."""
    if "cta_recommendations" in response:
        cta_rec = response["cta_recommendations"]
        cta_rec["primary"] = {
            "label": "Complete Purchase",
            "reason": "Checkout pages need clear completion action"
        }
    
    return response


def _apply_saas_pricing_templates(response: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Apply SaaS pricing page templates."""
    brand_ctx = ctx.get("brand_context", {})
    is_enterprise = brand_ctx.get("brand_maturity") == "enterprise"
    
    if "cta_recommendations" in response:
        cta_rec = response["cta_recommendations"]
        
        if is_enterprise:
            # Enterprise SaaS pricing
            cta_rec["primary"] = {
                "label": "Talk to Sales",
                "reason": "Enterprise pricing typically requires sales conversation"
            }
            cta_rec["secondary"] = [
                {"label": "Request Demo", "reason": "Enterprise buyers need to see the product"},
                {"label": "See Security & Compliance", "reason": "Enterprise buyers prioritize security"}
            ]
        else:
            # Growth SaaS pricing
            cta_rec["primary"] = {
                "label": "Start Free Trial",
                "reason": "Free trial reduces commitment risk for SaaS"
            }
            cta_rec["secondary"] = [
                {"label": "Compare Plans", "reason": "Helps users choose the right plan"},
                {"label": "See Features", "reason": "Clarifies plan differences"}
            ]
    
    # Update decision psychology insight
    if "decision_psychology_insight" in response:
        insight = response["decision_psychology_insight"]
        insight["headline"] = "Plan Differentiation and Next Step Clarity"
        insight["insight"] = "SaaS pricing pages need clear plan differentiation, next step clarity (trial vs sales), and FAQs to help users choose the right plan."
        insight["why_now"] = "Unclear plan differences and ambiguous next steps create decision delay."
        insight["micro_risk_reducer"] = "Add plan comparison table, clarify trial vs sales path, and include pricing calculator if applicable."
    
    return response


def _apply_leadgen_templates(response: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Apply lead generation and local service templates."""
    if "cta_recommendations" in response:
        cta_rec = response["cta_recommendations"]
        cta_rec["primary"] = {
            "label": "Book a Call",
            "reason": "Lead generation pages need booking/contact CTAs"
        }
        cta_rec["secondary"] = [
            {"label": "Get a Quote", "reason": "Alternative lead generation path"},
            {"label": "Schedule Appointment", "reason": "Direct booking action"}
        ]
        cta_rec["do_not_use"] = [
            {"label": "Learn More", "reason": "Too generic for lead generation pages"},
            {"label": "Get Started", "reason": "Not appropriate for service/consultation pages"}
        ]
    
    # Update decision psychology insight
    if "decision_psychology_insight" in response:
        insight = response["decision_psychology_insight"]
        insight["headline"] = "Credibility and Risk Reversal Drive Leads"
        insight["insight"] = "Lead generation and local service pages need credibility signals, social proof, risk reversal mechanisms, and low-friction booking to convert."
        insight["why_now"] = "Service buyers need trust and low commitment to book."
        insight["micro_risk_reducer"] = "Add 'No obligation' messaging, 'Reply in 24h' guarantee, and simplify booking form."
    
    # Update personas
    if "mindset_personas" in response:
        personas = response["mindset_personas"]
        for persona in personas:
            if persona.get("id") == "hesitant":
                persona["title"] = "Risk-Averse Service Seeker"
                persona["signal"] = "Needs credibility and risk reversal before booking"
                persona["goal"] = "Verify credibility and reduce commitment risk"
                persona["best_cta"] = "See Testimonials"
                persona["next_step"] = "Add testimonials, guarantees, and 'no obligation' messaging"
    
    return response


def _apply_enterprise_b2b_templates(response: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Apply enterprise B2B templates."""
    page_intent = ctx.get("page_intent", {})
    intent = page_intent.get("intent", "unknown")
    
    if "cta_recommendations" in response:
        cta_rec = response["cta_recommendations"]
        
        if intent == "pricing":
            cta_rec["primary"] = {
                "label": "Talk to Sales",
                "reason": "Enterprise pricing requires sales conversation"
            }
        elif intent == "enterprise_sales":
            cta_rec["primary"] = {
                "label": "Request Demo",
                "reason": "Enterprise buyers need to see the product"
            }
        else:
            cta_rec["primary"] = {
                "label": "See Security & Compliance",
                "reason": "Enterprise buyers prioritize security and compliance"
            }
    
    # Ensure no naive trust claims
    if "decision_psychology_insight" in response:
        insight = response["decision_psychology_insight"]
        # Avoid trust-related naive claims
        if "trust" in insight.get("headline", "").lower() and "missing" in insight.get("headline", "").lower():
            insight["headline"] = "Clarity and Cognitive Load Optimization"
            insight["insight"] = "Enterprise B2B pages need clarity, reduced cognitive load, and clear next steps rather than additional trust signals."
    
    return response


def _apply_content_blog_templates(response: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Apply content/blog page templates."""
    if "cta_recommendations" in response:
        cta_rec = response["cta_recommendations"]
        cta_rec["primary"] = {
            "label": "Subscribe",
            "reason": "Content pages focus on subscription and engagement"
        }
        cta_rec["secondary"] = [
            {"label": "Download Resource", "reason": "Content conversion goal"},
            {"label": "Read Related Content", "reason": "Engagement-focused CTA"}
        ]
    
    return response


def _apply_saas_home_templates(response: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Apply SaaS home page templates."""
    if "cta_recommendations" in response:
        cta_rec = response["cta_recommendations"]
        cta_rec["primary"] = {
            "label": "Start Free Trial",
            "reason": "SaaS home pages focus on trial signup"
        }
    
    return response

