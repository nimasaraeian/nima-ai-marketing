"""
Proxy Endpoints

Proxy endpoints for frontend compatibility.
These endpoints act as aliases or proxies to existing backend endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging

from api.decision_engine import DecisionEngineInput, analyze_decision_failure
from api.brain.evidence.integration import EvidenceContext, extract_all_evidence, enrich_decision_output
from api.brain.evidence.ad_signals import AdInput
from api.schemas.page_features import PageFeatures

router = APIRouter(prefix="/api/proxy", tags=["Proxy"])

logger = logging.getLogger("proxy")


class DecisionScanRequest(BaseModel):
    """Request for decision scan (evidence-based analysis)"""
    url: Optional[str] = Field(None, description="URL to analyze")
    content: Optional[str] = Field(None, description="Content text to analyze")
    goal: Optional[str] = Field(None, description="Analysis goal")
    
    # Evidence inputs
    landing_features: Optional[Dict[str, Any]] = Field(None, description="Landing page features")
    ad_copy: Optional[str] = Field(None, description="Ad copy text")
    ad_headline: Optional[str] = Field(None, description="Ad headline")
    pricing_html: Optional[str] = Field(None, description="Pricing page HTML")
    pricing_text: Optional[str] = Field(None, description="Pricing page text")


@router.post("/decision-scan")
async def decision_scan_proxy(request: DecisionScanRequest) -> Dict[str, Any]:
    """
    Proxy endpoint for decision scan with evidence.
    
    This endpoint:
    1. Extracts evidence from landing/ad/pricing sources
    2. Runs decision engine analysis
    3. Enriches output with evidence metadata
    
    Compatible with frontend evidence submission form.
    """
    try:
        # Build evidence context if evidence is provided
        evidence_result = None
        if request.landing_features or request.ad_copy or request.ad_headline or request.pricing_html or request.pricing_text:
            landing_features = None
            if request.landing_features:
                try:
                    landing_features = PageFeatures(**request.landing_features)
                except Exception as e:
                    logger.warning(f"Failed to parse landing_features: {e}")
            
            ad_input = None
            if request.ad_copy or request.ad_headline:
                ad_input = AdInput(
                    ad_copy=request.ad_copy,
                    ad_headline=request.ad_headline
                )
            
            context = EvidenceContext(
                landing_features=landing_features,
                ad_input=ad_input,
                pricing_html=request.pricing_html,
                pricing_text=request.pricing_text
            )
            
            evidence_result = extract_all_evidence(context)
            logger.info(f"Extracted evidence from {len(evidence_result['merged_signals'].signals.get('sources_used', []))} sources")
        
        # Run decision engine analysis
        decision_input = DecisionEngineInput(
            content=request.content or "",
            url=request.url,
            channel="generic_saas"  # Default, can be auto-detected
        )
        
        decision_result = await analyze_decision_failure(decision_input)
        decision_output = decision_result.dict()
        
        # Enrich with evidence if available
        if evidence_result:
            decision_output = enrich_decision_output(decision_output, evidence_result)
        
        # Add analysis status
        decision_output["analysisStatus"] = "ok"
        
        return decision_output
        
    except Exception as e:
        logger.exception(f"Decision scan failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Decision scan failed: {str(e)}"
        )


@router.get("/health")
async def proxy_health() -> Dict[str, str]:
    """Health check for proxy endpoints"""
    return {
        "status": "ok",
        "module": "proxy",
        "version": "1.0.0"
    }



