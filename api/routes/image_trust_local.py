from fastapi import APIRouter, UploadFile, File

from ..services.image_trust_service import analyze_image_trust_bytes

router = APIRouter(prefix="/api/analyze", tags=["image-trust-local"])


@router.post("/image-trust-local")
async def image_trust_local(file: UploadFile = File(...)):
    """Image trust analysis using OpenCV + local extractor (no TensorFlow)."""
    data = await file.read()
    return analyze_image_trust_bytes(data)




