from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class HumanQuickWin(BaseModel):
    title: str
    why: str
    how: List[str] = []
    impact: str = Field(..., description="high|medium|low")
    effort: str = Field(..., description="high|medium|low")
    related_blockers: List[str] = []


class HumanReportV1(BaseModel):
    url: str
    verdict: str
    decision_probability: float
    top_blockers: List[Dict[str, Any]] = []
    quick_wins: List[HumanQuickWin] = []
    evidence: List[str] = []
    visual_summary: Dict[str, Any] = {}
    public_summary: str = Field(..., description="5-6 line pitch-ready summary, fully grounded")
    debug: Dict[str, Any] = {}

