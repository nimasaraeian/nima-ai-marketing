"""
Evidence Extraction API Endpoints

Provides endpoints for extracting decision signals from:
- Landing pages
- Ad/Banner content
- Pricing pages
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from api.brain.evidence.integration import EvidenceContext, extract_all_evidence, enrich_decision_output
from api.brain.evidence.ad_signals import AdInput
from api.brain.evidence.landing_signals import extract_landing_signals
from api.schemas.page_features import PageFeatures

router = APIRouter(prefix="/api/brain/evidence", tags=["Evidence"])


class AdEvidenceInput(BaseModel):
    """Input for ad evidence extraction"""
    ad_copy: Optional[str] = Field(None, description="Ad copy text")
    ad_headline: Optional[str] = Field(None, description="Ad headline")
    ad_description: Optional[str] = Field(None, description="Ad description")
    image_url: Optional[str] = Field(None, description="Ad image URL")
    image_bytes: Optional[str] = Field(None, description="Ad image as base64 string")


class PricingEvidenceInput(BaseModel):
    """Input for pricing evidence extraction"""
    html: Optional[str] = Field(None, description="Pricing page HTML")
    text: Optional[str] = Field(None, description="Pricing page text")


class EvidenceExtractionRequest(BaseModel):
    """Request for evidence extraction"""
    landing_features: Optional[Dict[str, Any]] = Field(None, description="Landing page features (PageFeatures dict)")
    ad_evidence: Optional[AdEvidenceInput] = Field(None, description="Ad evidence")
    pricing_evidence: Optional[PricingEvidenceInput] = Field(None, description="Pricing evidence")


@router.post("/extract")
async def extract_evidence(request: EvidenceExtractionRequest) -> Dict[str, Any]:
    """
    Extract decision signals from multiple evidence sources.
    
    Returns merged signals and confidence score.
    """
    try:
        # Build evidence context
        landing_features = None
        if request.landing_features:
            try:
                landing_features = PageFeatures(**request.landing_features)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid landing_features format: {str(e)}"
                )
        
        ad_input = None
        if request.ad_evidence:
            ad_input = AdInput(
                ad_copy=request.ad_evidence.ad_copy,
                ad_headline=request.ad_evidence.ad_headline,
                ad_description=request.ad_evidence.ad_description,
                image_url=request.ad_evidence.image_url,
                image_bytes=request.ad_evidence.image_bytes.encode() if request.ad_evidence.image_bytes else None
            )
        
        pricing_html = request.pricing_evidence.html if request.pricing_evidence else None
        pricing_text = request.pricing_evidence.text if request.pricing_evidence else None
        
        context = EvidenceContext(
            landing_features=landing_features,
            ad_input=ad_input,
            pricing_html=pricing_html,
            pricing_text=pricing_text
        )
        
        # Extract all evidence
        evidence_result = extract_all_evidence(context)
        
        # Convert to dict for JSON response
        from api.brain.decision_signals import signals_to_dict
        
        response = {
            "sources_used": evidence_result["merged_signals"].signals.get("sources_used", []),
            "merged_signals": signals_to_dict(evidence_result["merged_signals"]),
            "confidence": evidence_result["confidence_score"],
            "landing_signals": signals_to_dict(evidence_result["landing_signals"]) if evidence_result.get("landing_signals") else None,
            "ad_signals": signals_to_dict(evidence_result["ad_signals"]) if evidence_result.get("ad_signals") else None,
            "pricing_signals": signals_to_dict(evidence_result["pricing_signals"]) if evidence_result.get("pricing_signals") else None,
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract evidence: {str(e)}"
        )


@router.get("/health")
async def evidence_health() -> Dict[str, str]:
    """Health check for evidence extraction module"""
    return {
        "status": "ok",
        "module": "evidence_extraction",
        "version": "1.0.0"
    }



