"""
Landing friction dataset pipeline utilities shared between scripts and API endpoints.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI
from pydantic import ValidationError

from data.landing_friction.schema.landing_sample_schema import (
    Label,
    LandingFrictionSample,
)

LOGGER = logging.getLogger("landing_friction")

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "data" / "landing_friction"
LABEL_DIRS: Dict[Label, Path] = {
    "low": DATA_ROOT / "low",
    "medium": DATA_ROOT / "medium",
    "high": DATA_ROOT / "high",
}
DATASET_PATH = DATA_ROOT / "dataset" / "landing_friction_dataset.json"
FINE_TUNE_JSONL_PATH = DATA_ROOT / "fine_tune" / "landing_friction_finetune.jsonl"
FINE_TUNE_META_PATH = DATA_ROOT / "fine_tune" / "last_finetune_job.json"

SYSTEM_PROMPT = (
    "You are a cognitive friction analysis model. Given landing-page content, "
    "you must output a JSON object describing friction scores. "
    "Follow the existing CognitiveFrictionResult schema exactly."
)


def ensure_directories() -> None:
    """Ensure all required landing friction directories exist."""
    for path in [
        DATA_ROOT,
        *LABEL_DIRS.values(),
        DATA_ROOT / "schema",
        DATA_ROOT / "dataset",
        DATA_ROOT / "fine_tune",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def _load_sample_file(path: Path, expected_label: Label) -> Optional[LandingFrictionSample]:
    """Load and validate one sample file."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        sample = LandingFrictionSample.model_validate(payload)
        if sample.label != expected_label:
            LOGGER.warning(
                "Label mismatch for %s: expected %s, found %s. Skipping.",
                path,
                expected_label,
                sample.label,
            )
            return None
        return sample
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        LOGGER.error("Invalid sample %s: %s", path, exc)
        return None


def _aggregate_samples() -> Tuple[List[LandingFrictionSample], List[str]]:
    """Collect samples from label folders."""
    ensure_directories()
    samples: List[LandingFrictionSample] = []
    invalid_files: List[str] = []

    for label, folder in LABEL_DIRS.items():
        for path in sorted(folder.glob("*.json")):
            sample = _load_sample_file(path, label)
            if sample:
                samples.append(sample)
            else:
                invalid_files.append(str(path))
    return samples, invalid_files


@dataclass
class DatasetBuildResult:
    total_samples: int
    counts_by_label: Dict[str, int]
    average_total_friction: Dict[str, float]
    output_path: str
    invalid_files: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_landing_friction_dataset() -> DatasetBuildResult:
    """Merge labeled samples into a single dataset JSON."""
    samples, invalid_files = _aggregate_samples()
    counts: Dict[str, int] = {label: 0 for label in LABEL_DIRS}
    totals: Dict[str, List[int]] = {label: [] for label in LABEL_DIRS}

    for sample in samples:
        counts[sample.label] += 1
        totals[sample.label].append(sample.total_friction)

    averages: Dict[str, float] = {
        label: round(mean(values), 2) if values else 0.0 for label, values in totals.items()
    }

    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATASET_PATH.open("w", encoding="utf-8") as fp:
        json.dump([sample.model_dump(mode="json") for sample in samples], fp, indent=2)

    LOGGER.info(
        "Landing friction dataset built: %s (samples=%s, invalid=%s)",
        DATASET_PATH,
        len(samples),
        len(invalid_files),
    )

    return DatasetBuildResult(
        total_samples=len(samples),
        counts_by_label=counts,
        average_total_friction=averages,
        output_path=str(DATASET_PATH),
        invalid_files=invalid_files,
    )


@dataclass
class FineTunePreparationResult:
    dataset_examples: int
    output_path: str
    dataset_summary: Optional[DatasetBuildResult] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if self.dataset_summary:
            payload["dataset_summary"] = self.dataset_summary.to_dict()
        return payload


def _load_dataset_records() -> List[LandingFrictionSample]:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            "Dataset file missing. Build the dataset before preparing fine-tune data."
        )
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    return [LandingFrictionSample.model_validate(obj) for obj in data]


def _build_assistant_payload(sample: LandingFrictionSample) -> Dict[str, Any]:
    if sample.expected_result:
        return sample.expected_result
    return {
        "total_friction": sample.total_friction,
        "dimensions": sample.dimensions.model_dump(),
        "analysis": sample.analysis,
        "quick_fixes": sample.quick_fixes,
        "rewrite_examples": sample.rewrite_examples,
    }


def prepare_landing_friction_finetune(force_rebuild: bool = False) -> FineTunePreparationResult:
    """Create OpenAI fine-tune JSONL file."""
    dataset_summary: Optional[DatasetBuildResult] = None
    if force_rebuild or not DATASET_PATH.exists():
        dataset_summary = build_landing_friction_dataset()

    samples = _load_dataset_records()
    FINE_TUNE_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)

    user_template = (
        "Sample ID: {id}\n"
        "Label: {label}\n"
        "{url_section}"
        "Landing Page Content:\n{content}"
    )

    with FINE_TUNE_JSONL_PATH.open("w", encoding="utf-8") as fp:
        for sample in samples:
            url_section = f"URL: {sample.url}\n" if sample.url else ""
            user_message = user_template.format(
                id=sample.id,
                label=sample.label,
                url_section=url_section,
                content=sample.content,
            )
            assistant_payload = _build_assistant_payload(sample)
            record = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                    {
                        "role": "assistant",
                        "content": json.dumps(assistant_payload, ensure_ascii=False),
                    },
                ]
            }
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")

    LOGGER.info(
        "Prepared fine-tune JSONL: %s (examples=%s)",
        FINE_TUNE_JSONL_PATH,
        len(samples),
    )

    return FineTunePreparationResult(
        dataset_examples=len(samples),
        output_path=str(FINE_TUNE_JSONL_PATH),
        dataset_summary=dataset_summary,
    )


@dataclass
class FineTuneJobInfo:
    job_id: str
    status: str
    model: Optional[str]
    created_at: int
    training_file: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _get_client() -> OpenAI:
    """Instantiate OpenAI client using environment configuration."""
    return OpenAI()


def start_landing_friction_finetune(base_model: str = "gpt-4.1-mini") -> FineTuneJobInfo:
    """Upload JSONL file and start a fine-tuning job."""
    if not FINE_TUNE_JSONL_PATH.exists():
        raise FileNotFoundError(
            "Fine-tune JSONL file not found. Run prepare_landing_friction_finetune first."
        )

    client = _get_client()
    with FINE_TUNE_JSONL_PATH.open("rb") as training_file:
        uploaded = client.files.create(file=training_file, purpose="fine-tune")

    job = client.fine_tuning.jobs.create(
        training_file=uploaded.id,
        model=base_model,
    )

    info = FineTuneJobInfo(
        job_id=job.id,
        status=job.status,
        model=job.fine_tuned_model,
        created_at=job.created_at,
        training_file=uploaded.id,
    )
    FINE_TUNE_META_PATH.parent.mkdir(parents=True, exist_ok=True)
    FINE_TUNE_META_PATH.write_text(json.dumps(info.to_dict(), indent=2), encoding="utf-8")
    LOGGER.info("Fine-tune job created: %s", info.job_id)
    return info


def load_last_finetune_job() -> Optional[FineTuneJobInfo]:
    """Return the last recorded fine-tune job metadata if available."""
    if not FINE_TUNE_META_PATH.exists():
        return None
    data = json.loads(FINE_TUNE_META_PATH.read_text(encoding="utf-8"))
    return FineTuneJobInfo(**data)


def get_finetuned_model_id() -> Optional[str]:
    """Return the fine-tuned model id if available."""
    job = load_last_finetune_job()
    return job.model if job else None

