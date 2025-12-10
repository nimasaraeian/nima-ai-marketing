"""
Decision Stage Inference v1.0

Infers the mental decision stage of the user from the decision environment
(page structure, CTA, offer type, risk level) — not from behavioral tracking.

CORE PRINCIPLE: We do NOT track the user journey.
We infer the decision stage from the decision context.
Journey here means mental decision phase, not navigation history.
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger("decision_stage")


class DecisionStage(str, Enum):
    """Decision stages based on mental decision phase"""
    ORIENTATION = "orientation"
    SENSE_MAKING = "sense_making"
    EVALUATION = "evaluation"
    COMMITMENT = "commitment"
    POST_DECISION_VALIDATION = "post_decision_validation"


class FrictionSeverity(str, Enum):
    """Friction severity based on stage context"""
    NATURAL = "natural"  # Expected at this stage, don't fix
    ACCEPTABLE = "acceptable"  # Normal, guidance preferred
    WARNING = "warning"  # Should be addressed
    CRITICAL = "critical"  # Must be fixed immediately
    HIGH_RISK = "high_risk"  # Dangerous, likely causes abandonment


@dataclass
class StageInference:
    """Inferred decision stage with reasoning"""
    stage: DecisionStage
    confidence: float  # 0-100
    signals: List[str]  # What signals led to this inference
    explanation: str


@dataclass
class StageFrictionAssessment:
    """Assessment of friction severity at a given stage"""
    outcome: str
    stage: DecisionStage
    severity: FrictionSeverity
    reasoning: str
    recommendation: str  # What to do about it


class DecisionStageInference:
    """
    Infers decision stage from page context.
    """
    
    # CTA language patterns by stage
    ORIENTATION_CTAS = [
        "what is", "how it works", "learn about", "discover", "explore",
        "find out", "understand", "see what", "get to know"
    ]
    
    SENSE_MAKING_CTAS = [
        "learn more", "see how", "find out if", "discover if", "explore",
        "see if", "check if", "understand if", "is this for me"
    ]
    
    EVALUATION_CTAS = [
        "compare", "see pricing", "view plans", "check features",
        "see options", "view details", "learn more about"
    ]
    
    COMMITMENT_CTAS = [
        "buy", "purchase", "order", "book", "sign up", "get started",
        "start trial", "subscribe", "join", "add to cart", "checkout",
        "pay", "complete purchase", "confirm", "place order"
    ]
    
    POST_DECISION_CTAS = [
        "what happens next", "what to expect", "getting started",
        "next steps", "welcome", "thank you", "confirmation"
    ]
    
    def infer_stage(
        self,
        cta_text: Optional[str] = None,
        page_content: Optional[str] = None,
        has_pricing: bool = False,
        has_form: bool = False,
        has_checkout: bool = False,
        has_education: bool = False,
        has_comparison: bool = False,
        has_confirmation: bool = False,
        offer_type: Optional[str] = None
    ) -> StageInference:
        """
        Infer decision stage from context signals.
        
        Args:
            cta_text: Primary CTA button text
            page_content: Full page content (for pattern matching)
            has_pricing: Whether pricing is visible
            has_form: Whether form is present
            has_checkout: Whether checkout/booking flow is present
            has_education: Whether educational content is prominent
            has_comparison: Whether comparison/features table is present
            has_confirmation: Whether this is a confirmation page
            offer_type: Type of offer (trial, purchase, subscription, etc.)
        
        Returns:
            StageInference with stage, confidence, and reasoning
        """
        signals = []
        stage_scores: Dict[DecisionStage, float] = {
            DecisionStage.ORIENTATION: 0.0,
            DecisionStage.SENSE_MAKING: 0.0,
            DecisionStage.EVALUATION: 0.0,
            DecisionStage.COMMITMENT: 0.0,
            DecisionStage.POST_DECISION_VALIDATION: 0.0,
        }
        
        # Check for post-decision validation first (most specific)
        if has_confirmation:
            stage_scores[DecisionStage.POST_DECISION_VALIDATION] += 50.0
            signals.append("Confirmation page detected")
        
        if cta_text:
            cta_lower = cta_text.lower()
            content_lower = (page_content or "").lower()
            
            # Post-decision validation signals
            if any(phrase in cta_lower for phrase in self.POST_DECISION_CTAS):
                stage_scores[DecisionStage.POST_DECISION_VALIDATION] += 40.0
                signals.append(f"Post-decision CTA language: '{cta_text}'")
            
            # Commitment signals (strongest)
            if any(phrase in cta_lower for phrase in self.COMMITMENT_CTAS):
                stage_scores[DecisionStage.COMMITMENT] += 50.0
                signals.append(f"Commitment CTA language: '{cta_text}'")
            
            # Evaluation signals
            elif any(phrase in cta_lower for phrase in self.EVALUATION_CTAS):
                stage_scores[DecisionStage.EVALUATION] += 40.0
                signals.append(f"Evaluation CTA language: '{cta_text}'")
            
            # Sense-making signals
            elif any(phrase in cta_lower for phrase in self.SENSE_MAKING_CTAS):
                stage_scores[DecisionStage.SENSE_MAKING] += 40.0
                signals.append(f"Sense-making CTA language: '{cta_text}'")
            
            # Orientation signals
            elif any(phrase in cta_lower for phrase in self.ORIENTATION_CTAS):
                stage_scores[DecisionStage.ORIENTATION] += 40.0
                signals.append(f"Orientation CTA language: '{cta_text}'")
        
        # Structural cues
        if has_checkout or has_form:
            stage_scores[DecisionStage.COMMITMENT] += 30.0
            signals.append("Checkout/form present")
        
        if has_pricing:
            stage_scores[DecisionStage.EVALUATION] += 25.0
            stage_scores[DecisionStage.COMMITMENT] += 15.0
            signals.append("Pricing visible")
        
        if has_comparison:
            stage_scores[DecisionStage.EVALUATION] += 30.0
            signals.append("Comparison/features table present")
        
        if has_education and not has_pricing:
            stage_scores[DecisionStage.ORIENTATION] += 25.0
            stage_scores[DecisionStage.SENSE_MAKING] += 15.0
            signals.append("Educational content prominent")
        
        # Offer type signals
        if offer_type:
            if offer_type in ["trial", "demo", "free"]:
                stage_scores[DecisionStage.SENSE_MAKING] += 20.0
                stage_scores[DecisionStage.COMMITMENT] += 10.0
                signals.append(f"Low-commitment offer: {offer_type}")
            elif offer_type in ["purchase", "subscription", "booking"]:
                stage_scores[DecisionStage.COMMITMENT] += 25.0
                signals.append(f"High-commitment offer: {offer_type}")
        
        # Determine winning stage
        max_score = max(stage_scores.values())
        if max_score == 0:
            # Default to sense-making if no clear signals
            # This is a fallback only when no signals are detected
            logger.warning("[Decision Stage] No clear stage signals detected. Using fallback: sense-making")
            inferred_stage = DecisionStage.SENSE_MAKING
            confidence = 50.0
            explanation = "No clear stage signals detected. Defaulting to sense-making."
        else:
            inferred_stage = max(stage_scores.items(), key=lambda x: x[1])[0]
            confidence = min(100.0, max_score)
            explanation = f"Inferred {inferred_stage.value} stage with {confidence:.0f}% confidence based on: {', '.join(signals[:3])}"
        
        return StageInference(
            stage=inferred_stage,
            confidence=confidence,
            signals=signals,
            explanation=explanation
        )
    
    def assess_friction_severity(
        self,
        outcome: str,
        stage: DecisionStage
    ) -> StageFrictionAssessment:
        """
        Assess whether a detected outcome is natural or critical at this stage.
        
        Returns:
            StageFrictionAssessment with severity and recommendation
        """
        # Stage × Outcome interaction matrix
        severity_matrix = {
            DecisionStage.ORIENTATION: {
                "Outcome Unclear": FrictionSeverity.NATURAL,
                "Trust Gap": FrictionSeverity.NATURAL,
                "Risk Not Addressed": FrictionSeverity.ACCEPTABLE,
                "Effort Too High": FrictionSeverity.ACCEPTABLE,
                "Commitment Anxiety": FrictionSeverity.NATURAL,
            },
            DecisionStage.SENSE_MAKING: {
                "Outcome Unclear": FrictionSeverity.WARNING,
                "Trust Gap": FrictionSeverity.ACCEPTABLE,
                "Risk Not Addressed": FrictionSeverity.ACCEPTABLE,
                "Effort Too High": FrictionSeverity.ACCEPTABLE,
                "Commitment Anxiety": FrictionSeverity.NATURAL,
            },
            DecisionStage.EVALUATION: {
                "Outcome Unclear": FrictionSeverity.CRITICAL,
                "Trust Gap": FrictionSeverity.WARNING,
                "Risk Not Addressed": FrictionSeverity.CRITICAL,
                "Effort Too High": FrictionSeverity.WARNING,
                "Commitment Anxiety": FrictionSeverity.WARNING,
            },
            DecisionStage.COMMITMENT: {
                "Outcome Unclear": FrictionSeverity.HIGH_RISK,
                "Trust Gap": FrictionSeverity.CRITICAL,
                "Risk Not Addressed": FrictionSeverity.HIGH_RISK,
                "Effort Too High": FrictionSeverity.HIGH_RISK,
                "Commitment Anxiety": FrictionSeverity.CRITICAL,
            },
            DecisionStage.POST_DECISION_VALIDATION: {
                "Outcome Unclear": FrictionSeverity.CRITICAL,
                "Trust Gap": FrictionSeverity.CRITICAL,
                "Risk Not Addressed": FrictionSeverity.HIGH_RISK,
                "Effort Too High": FrictionSeverity.WARNING,
                "Commitment Anxiety": FrictionSeverity.CRITICAL,
            },
        }
        
        severity = severity_matrix.get(stage, {}).get(
            outcome,
            FrictionSeverity.WARNING
        )
        
        # Generate reasoning and recommendation
        reasoning_map = {
            (DecisionStage.ORIENTATION, "Trust Gap"): (
                "Trust signals are not yet critical at orientation stage. "
                "Users are still exploring and don't need full credibility yet."
            ),
            (DecisionStage.ORIENTATION, "Outcome Unclear"): (
                "Some ambiguity is natural when users are first learning. "
                "The goal is guidance, not conversion."
            ),
            (DecisionStage.ORIENTATION, "Effort Too High"): (
                "Cognitive load is acceptable during orientation. "
                "Users expect to invest effort in understanding."
            ),
            (DecisionStage.SENSE_MAKING, "Commitment Anxiety"): (
                "Commitment concerns are natural when users are checking relevance. "
                "Heavy CTAs would be premature here."
            ),
            (DecisionStage.EVALUATION, "Risk Not Addressed"): (
                "Risk becomes critical during evaluation. "
                "Users need clear policies to make informed decisions."
            ),
            (DecisionStage.EVALUATION, "Trust Gap"): (
                "Trust becomes more important during evaluation. "
                "Users are comparing options and need credibility signals."
            ),
            (DecisionStage.COMMITMENT, "Outcome Unclear"): (
                "Unclear outcomes at commitment stage are highly dangerous. "
                "Users need certainty before taking action."
            ),
            (DecisionStage.COMMITMENT, "Trust Gap"): (
                "Trust gaps at commitment are critical. "
                "Users won't proceed without sufficient credibility."
            ),
            (DecisionStage.COMMITMENT, "Effort Too High"): (
                "High cognitive effort at commitment causes abandonment. "
                "The decision should feel simple and clear."
            ),
            (DecisionStage.POST_DECISION_VALIDATION, "Trust Gap"): (
                "Trust reinforcement is required after decision. "
                "Users need reassurance to prevent regret."
            ),
        }
        
        reasoning = reasoning_map.get(
            (stage, outcome),
            f"{outcome} at {stage.value} stage"
        )
        
        # Generate recommendation based on severity
        if severity == FrictionSeverity.NATURAL:
            recommendation = (
                f"This friction is natural at {stage.value} stage. "
                "Do NOT fix it. Focus on guidance and education instead."
            )
        elif severity == FrictionSeverity.ACCEPTABLE:
            recommendation = (
                f"This friction is acceptable at {stage.value} stage. "
                "Consider gentle guidance rather than aggressive fixes."
            )
        elif severity == FrictionSeverity.WARNING:
            recommendation = (
                f"This friction should be addressed at {stage.value} stage. "
                "It may prevent progression to the next stage."
            )
        elif severity == FrictionSeverity.CRITICAL:
            recommendation = (
                f"This friction is CRITICAL at {stage.value} stage. "
                "It must be fixed immediately to prevent abandonment."
            )
        else:  # HIGH_RISK
            recommendation = (
                f"This friction is HIGHLY DANGEROUS at {stage.value} stage. "
                "It likely causes immediate abandonment. Fix urgently."
            )
        
        return StageFrictionAssessment(
            outcome=outcome,
            stage=stage,
            severity=severity,
            reasoning=reasoning,
            recommendation=recommendation
        )


# Global instance
decision_stage_inference = DecisionStageInference()

