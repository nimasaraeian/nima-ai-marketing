"""
Psychology dashboard schema for cognitive friction analysis.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class PersonalityActivation(BaseModel):
    O: int = Field(..., ge=0, le=100)
    C: int = Field(..., ge=0, le=100)
    E: int = Field(..., ge=0, le=100)
    A: int = Field(..., ge=0, le=100)
    N: int = Field(..., ge=0, le=100)
    dominant_profile: str
    explanation: str


class CognitiveStyle(BaseModel):
    type: Literal["analytical", "intuitive", "overloaded", "mixed"]
    overload_risk: int = Field(..., ge=0, le=100)
    ambiguity_aversion: int = Field(..., ge=0, le=100)
    explanation: str


class EmotionalResponse(BaseModel):
    curiosity: int = Field(..., ge=0, le=100)
    excitement: int = Field(..., ge=0, le=100)
    motivation: int = Field(..., ge=0, le=100)
    anxiety: int = Field(..., ge=0, le=100)
    confusion: int = Field(..., ge=0, le=100)
    trust: int = Field(..., ge=0, le=100)


class DecisionFrame(BaseModel):
    mode: Literal["gain_seeking", "loss_avoidance", "neutral"]
    risk_style: Literal["risk_averse", "risk_taking", "moderate"]
    decision_tendency: Literal["move_forward", "hesitate", "postpone", "bounce"]
    explanation: str


class TrustDynamics(BaseModel):
    visual_trust: int = Field(..., ge=0, le=100)
    institutional_trust: int = Field(..., ge=0, le=100)
    social_trust: int = Field(..., ge=0, le=100)
    skepticism: int = Field(..., ge=0, le=100)


class MotivationStyle(BaseModel):
    primary: str
    secondary: Optional[str] = None
    explanation: str


class CognitiveLoadProfile(BaseModel):
    clarity_score: int = Field(..., ge=0, le=100)
    overload_score: int = Field(..., ge=0, le=100)
    ambiguity_score: int = Field(..., ge=0, le=100)


class BehavioralPrediction(BaseModel):
    convert: int = Field(..., ge=0, le=100)
    hesitate: int = Field(..., ge=0, le=100)
    bounce: int = Field(..., ge=0, le=100)
    postpone: int = Field(..., ge=0, le=100)
    summary: str


class AttentionMap(BaseModel):
    hotspots: List[str]
    friction_points: List[str]


class EmotionalTriggers(BaseModel):
    activated: List[str]
    missing: List[str]


class MemoryActivation(BaseModel):
    semantic: int = Field(..., ge=0, le=100)
    emotional: int = Field(..., ge=0, le=100)
    pattern: int = Field(..., ge=0, le=100)


class RiskPerception(BaseModel):
    risk_level: int = Field(..., ge=0, le=100)
    uncertainty_points: List[str]


class CTAMatch(BaseModel):
    fit_score: int = Field(..., ge=0, le=100)
    clarity: int = Field(..., ge=0, le=100)
    motivation_alignment: int = Field(..., ge=0, le=100)
    action_probability: int = Field(..., ge=0, le=100)


class PsychologyDashboard(BaseModel):
    personality_activation: PersonalityActivation
    cognitive_style: CognitiveStyle
    emotional_response: EmotionalResponse
    decision_frame: DecisionFrame
    trust_dynamics: TrustDynamics
    motivation_style: MotivationStyle
    cognitive_load: CognitiveLoadProfile
    behavioral_prediction: BehavioralPrediction
    attention_map: AttentionMap
    emotional_triggers: EmotionalTriggers
    memory_activation: MemoryActivation
    risk_perception: RiskPerception
    cta_match: CTAMatch







