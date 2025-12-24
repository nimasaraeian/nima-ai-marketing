"""
Tests for Personal Brand / Consultant page type personas.
"""
import pytest
from api.brain.decision_engine.persona_templates import build_personas
from api.brain.decision_engine.cost_templates import build_cost_of_inaction


def test_personal_brand_personas():
    """Test that personal brand personas reference expert fit, not trust badges."""
    personas = build_personas("personal_brand_consultant", {})
    
    assert len(personas) == 3
    assert personas[0]["id"] == "hesitant"
    assert personas[1]["id"] == "curious"
    assert personas[2]["id"] == "ready"
    
    # Check hesitant persona
    hesitant = personas[0]
    assert "personal fit" in hesitant["signal"].lower() or "outcome expectations" in hesitant["signal"].lower()
    assert "expert" in hesitant["goal"].lower() or "problem" in hesitant["goal"].lower()
    assert "see how i can help" in hesitant["best_cta"].lower()
    
    # Check curious persona
    curious = personas[1]
    assert "credibility" in curious["signal"].lower() or "thinking alignment" in curious["signal"].lower()
    assert "expertise" in curious["goal"].lower() or "approach" in curious["goal"].lower()
    assert "case examples" in curious["best_cta"].lower() or "case" in curious["best_cta"].lower()
    
    # Check ready persona
    ready = personas[2]
    assert "trust established" in ready["signal"].lower() or "action path" in ready["signal"].lower()
    assert "low-risk" in ready["goal"].lower() or "conversation" in ready["goal"].lower()
    assert "book a call" in ready["best_cta"].lower()
    
    # Ensure no ecommerce language
    all_text = " ".join([p["signal"] + " " + p["goal"] + " " + p["best_cta"] for p in personas]).lower()
    assert "add to cart" not in all_text
    assert "buy now" not in all_text
    assert "checkout" not in all_text


def test_personal_brand_cost_of_inaction():
    """Test that personal brand cost of inaction is context-appropriate."""
    cost = build_cost_of_inaction("personal_brand_consultant")
    
    assert cost["headline"] == "What This Delay Is Costing You"
    assert len(cost["bullets"]) == 3
    assert "problem resolution" in cost["bullets"][0].lower() or "decision hesitation" in cost["bullets"][0].lower()
    assert "momentum" in cost["bullets"][1].lower() or "evaluating" in cost["bullets"][1].lower()
    assert "uncertainty" in cost["bullets"][2].lower() or "strategic direction" in cost["bullets"][2].lower()
    assert "time-to-contact" in cost["metric_hint"].lower() or "qualified inquiries" in cost["metric_hint"].lower()
    
    # Ensure no ecommerce language
    all_text = " ".join(cost["bullets"]).lower()
    assert "conversion rate" not in all_text
    assert "cart abandonment" not in all_text


def test_b2b_corporate_personas():
    """Test that B2B corporate personas reference internal approval, not trust badges."""
    personas = build_personas("b2b_corporate_service", {})
    
    assert len(personas) == 3
    assert personas[0]["id"] == "hesitant"
    assert personas[1]["id"] == "curious"
    assert personas[2]["id"] == "ready"
    
    # Check hesitant persona (organizational risk)
    hesitant = personas[0]
    assert "internal approval" in hesitant["signal"].lower() or "decision risk" in hesitant["signal"].lower()
    assert "vendor choice" in hesitant["goal"].lower() or "wrong" in hesitant["goal"].lower()
    assert "understand our approach" in hesitant["best_cta"].lower()
    assert "internal justification" in hesitant["next_step"].lower()
    
    # Check curious persona
    curious = personas[1]
    assert "comparing providers" in curious["signal"].lower() or "scope" in curious["signal"].lower()
    assert "fit and capability" in curious["goal"].lower() or "assess" in curious["goal"].lower()
    assert "relevant projects" in curious["best_cta"].lower() or "projects" in curious["best_cta"].lower()
    
    # Check ready persona
    ready = personas[2]
    assert "aligned internally" in ready["signal"].lower() or "next step unclear" in ready["signal"].lower()
    assert "move decision forward" in ready["goal"].lower() or "safely" in ready["goal"].lower()
    assert "contact the team" in ready["best_cta"].lower()
    
    # Ensure no ecommerce language
    all_text = " ".join([p["signal"] + " " + p["goal"] + " " + p["best_cta"] for p in personas]).lower()
    assert "add to cart" not in all_text
    assert "buy now" not in all_text
    assert "checkout" not in all_text


def test_b2b_corporate_cost_of_inaction():
    """Test that B2B corporate cost of inaction is organization-focused."""
    cost = build_cost_of_inaction("b2b_corporate_service")
    
    assert cost["headline"] == "What This Delay Is Costing the Organization"
    assert len(cost["bullets"]) == 3
    assert "internal decision cycles" in cost["bullets"][0].lower() or "decision cycles" in cost["bullets"][0].lower()
    assert "qualified leads" in cost["bullets"][1].lower() or "evaluation" in cost["bullets"][1].lower()
    assert "projects postponed" in cost["bullets"][2].lower() or "next steps" in cost["bullets"][2].lower()
    assert "sales cycle" in cost["metric_hint"].lower() or "lead-to-meeting" in cost["metric_hint"].lower()
    
    # Ensure no ecommerce language
    all_text = " ".join(cost["bullets"]).lower()
    assert "conversion rate" not in all_text
    assert "cart abandonment" not in all_text


def test_personas_differ_by_page_type():
    """Test that personas differ across page types."""
    personal_personas = build_personas("personal_brand_consultant", {})
    b2b_personas = build_personas("b2b_corporate_service", {})
    ecommerce_personas = build_personas("ecommerce_product", {})
    
    # Personal brand should reference expert fit
    personal_hesitant = personal_personas[0]["signal"]
    assert "personal fit" in personal_hesitant.lower() or "expert" in personal_hesitant.lower()
    
    # B2B should reference organizational risk
    b2b_hesitant = b2b_personas[0]["signal"]
    assert "internal" in b2b_hesitant.lower() or "vendor" in b2b_hesitant.lower()
    
    # Ecommerce should reference shopping risk
    ecommerce_hesitant = ecommerce_personas[0]["signal"]
    assert "returns" in ecommerce_hesitant.lower() or "shipping" in ecommerce_hesitant.lower() or "payment" in ecommerce_hesitant.lower()


def test_cost_differ_by_page_type():
    """Test that cost of inaction differs across page types."""
    personal_cost = build_cost_of_inaction("personal_brand_consultant")
    b2b_cost = build_cost_of_inaction("b2b_corporate_service")
    ecommerce_cost = build_cost_of_inaction("ecommerce_product")
    
    # Personal brand should focus on individual delay
    assert "costing you" in personal_cost["headline"].lower()
    assert "problem resolution" in personal_cost["bullets"][0].lower() or "decision hesitation" in personal_cost["bullets"][0].lower()
    
    # B2B should focus on organization
    assert "costing the organization" in b2b_cost["headline"].lower()
    assert "internal decision" in b2b_cost["bullets"][0].lower() or "decision cycles" in b2b_cost["bullets"][0].lower()
    
    # Ecommerce should focus on conversion metrics
    assert "conversion rate" in ecommerce_cost["bullets"][0].lower() or "cart abandonment" in ecommerce_cost["bullets"][1].lower()

