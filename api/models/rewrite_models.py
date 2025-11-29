"""Pydantic models for rewrite engine"""
from pydantic import BaseModel, Field
from typing import List


class RewriteInput(BaseModel):
    """Input schema for text rewrite"""
    text: str = Field(..., description="The original text to rewrite")
    platform: str = Field(..., description="Platform: landing_page, instagram, linkedin, email, etc.")
    goal: List[str] = Field(..., description="Goals: clicks, leads, sales, engagement, etc.")
    audience: str = Field(..., description="Audience type: cold, warm, retargeting, etc.")
    language: str = Field(default="en", description="Language code: en, tr, fa, etc.")


class RewriteOutput(BaseModel):
    """Output schema for rewritten text versions"""
    soft_version: str = Field(..., description="Soft trust-based version")
    value_version: str = Field(..., description="Value-based version")
    proof_version: str = Field(..., description="Proof-driven version")
    emotional_version: str = Field(..., description="Emotional version")
    direct_version: str = Field(..., description="High-conversion direct version")
    cta: str = Field(..., description="Optimized call-to-action")

