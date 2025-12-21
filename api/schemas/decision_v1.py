from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class DecisionBlocker(BaseModel):
    id: str
    severity: str = Field(..., description="low|medium|high")
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: List[str] = []
    metrics: Dict[str, Any] = {}


class DecisionLogicV1(BaseModel):
    url: str
    signals_version: str = "signals_v1"
    decision_version: str = "decision_v1"

    blockers: List[DecisionBlocker] = []
    scores: Dict[str, float] = {}          # e.g., {"clarity": 0.55, "trust": 0.35, "friction": 0.60}
    decision_probability: float = Field(..., ge=0.0, le=1.0)

    # debugging / transparency
    weights: Dict[str, float] = {}
    inputs: Dict[str, Any] = {}

