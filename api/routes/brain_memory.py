from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.memory.brain_memory import insert_feedback, calibrate_weights, analysis_exists


router = APIRouter(prefix="/api/brain", tags=["brain-memory"])


class FeedbackRequest(BaseModel):
    analysis_id: int = Field(..., description="ID returned from /api/analyze/url-human")
    label: str = Field(..., pattern="^(accurate|partial|wrong)$")
    notes: Optional[str] = None
    wrong_issues: Optional[List[str]] = None


@router.post("/feedback")
async def submit_feedback(payload: FeedbackRequest) -> Dict[str, Any]:
    """
    Store user feedback for a specific analysis.

    Body:
    {
      "analysis_id": 123,
      "label": "accurate" | "partial" | "wrong",
      "notes": "...",
      "wrong_issues": ["missing_primary_cta", "h1_clarity"]
    }
    """
    # Validate analysis_id exists
    if not analysis_exists(payload.analysis_id):
        raise HTTPException(
            status_code=404,
            detail=f"Analysis with id={payload.analysis_id} not found",
        )

    # Validate wrong_issues logic
    wrong_issues = payload.wrong_issues or []
    if payload.label != "wrong" and wrong_issues:
        raise HTTPException(
            status_code=400,
            detail="wrong_issues must be empty unless label is 'wrong'",
        )

    try:
        feedback_id = insert_feedback(
            analysis_id=payload.analysis_id,
            label=payload.label,
            notes=payload.notes,
            wrong_issues=wrong_issues,
        )
        return {
            "status": "ok",
            "feedback_id": feedback_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calibrate")
async def calibrate() -> Dict[str, Any]:
    """
    Run daily calibration job (can be called manually).

    For each (page_type, issue_id):
      suggested_count = count where issue_id appears in analyses.top_issues
      accurate_count  = count feedback.label == accurate (partial counts as 0.5)
      wrong_count     = count feedback.label == wrong OR wrong_issues contains issue_id

    weight = clamp(0.2, 1.8, 1.0 + 0.6*(accurate_count - wrong_count)/max(1, suggested_count))
    """
    try:
        result = calibrate_weights()
        return {
            "status": "ok",
            "weights_updated": result.get("weights_updated", 0),
            "distinct_pairs": result.get("distinct_pairs", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


