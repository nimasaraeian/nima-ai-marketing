from fastapi import APIRouter

from api.schemas.page_features import PageFeatures
from api.brain.decision_brain import analyze_decision

router = APIRouter(prefix="/api/brain", tags=["brain-features"])


@router.post("/analyze-features")
async def analyze_features_endpoint(features: PageFeatures):
    result = analyze_decision(features)
    return {
        "analysisStatus": "ok",
        "featuresSchemaVersion": features.featuresSchemaVersion,
        "brain": result,
    }








