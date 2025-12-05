"""
FastAPI router for landing friction dataset training operations.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException

from landing_friction.pipeline import (
    build_landing_friction_dataset,
    get_finetuned_model_id,
    load_last_finetune_job,
    prepare_landing_friction_finetune,
    start_landing_friction_finetune,
)

router = APIRouter()
LOGGER = logging.getLogger("landing_friction")


@router.post("/api/training/landing-friction/build-dataset")
async def build_landing_friction_dataset_endpoint() -> dict:
    """
    Build the merged landing friction dataset.
    """
    result = build_landing_friction_dataset()
    return result.to_dict()


@router.post("/api/training/landing-friction/prepare-finetune")
async def prepare_landing_friction_finetune_endpoint(force_rebuild: bool = False) -> dict:
    """
    Prepare fine-tune JSONL file, optionally rebuilding the dataset first.
    """
    result = prepare_landing_friction_finetune(force_rebuild=force_rebuild)
    return result.to_dict()


@router.post("/api/training/landing-friction/start-finetune")
async def start_landing_friction_finetune_endpoint(base_model: str = "gpt-4.1-mini") -> dict:
    """
    Start a fine-tuning job on OpenAI using the prepared dataset.
    """
    try:
        job_info = start_landing_friction_finetune(base_model=base_model)
        return job_info.to_dict()
    except FileNotFoundError as err:
        LOGGER.error("Fine-tune start failed: %s", err)
        raise HTTPException(status_code=400, detail=str(err)) from err
    except Exception as err:
        LOGGER.exception("OpenAI fine-tune job failed")
        raise HTTPException(status_code=500, detail=str(err)) from err


@router.get("/api/training/landing-friction/last-job")
async def get_last_finetune_job() -> dict:
    """
    Return metadata about the last fine-tune job if available.
    """
    job = load_last_finetune_job()
    if not job:
        raise HTTPException(status_code=404, detail="No fine-tune job recorded yet.")
    return job.to_dict()


@router.get("/api/training/landing-friction/model")
async def get_finetuned_model() -> dict:
    """
    Return the current fine-tuned model id if available.
    """
    model_id = get_finetuned_model_id()
    if not model_id:
        raise HTTPException(status_code=404, detail="Fine-tuned model not available.")
    return {"model": model_id}






