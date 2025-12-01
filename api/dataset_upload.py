from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import Literal
import shutil
import csv
import os
from datetime import datetime

# Trust labels allowed for this first version
TrustLabel = Literal["high", "medium", "low"]

router = APIRouter(prefix="/api/dataset", tags=["dataset"])


def get_project_root() -> Path:
    """
    Resolve the project root directory (one level above the api folder).
    """
    return Path(__file__).parent.parent


def get_dataset_paths(trust_label: TrustLabel) -> tuple[Path, Path]:
    """
    Compute the target image directory and CSV log path for a given trust label.
    """
    project_root = get_project_root()
    dataset_root = project_root / "dataset"
    images_root = dataset_root / "images"

    # Map short labels to folder names
    folder_map = {
        "high": "high_trust",
        "medium": "medium_trust",
        "low": "low_trust",
    }

    label_folder = images_root / folder_map[trust_label]
    labels_csv = dataset_root / "labels.csv"
    return label_folder, labels_csv


def ensure_directories_and_csv(label_folder: Path, labels_csv: Path) -> None:
    """
    Make sure directories exist and labels.csv has a header if newly created.
    """
    label_folder.mkdir(parents=True, exist_ok=True)
    labels_csv.parent.mkdir(parents=True, exist_ok=True)

    if not labels_csv.exists():
        # Create CSV with header
        with labels_csv.open(mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["filename", "trust_label"])


def save_uploaded_file(label_folder: Path, upload_file: UploadFile) -> Path:
    """
    Save the uploaded image file to the target folder.
    Uses a timestamp prefix to avoid collisions.
    """
    original_name = os.path.basename(upload_file.filename or "")
    if not original_name:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    # Add timestamp prefix to avoid overwriting existing files
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
    target_name = f"{timestamp}_{original_name}"
    target_path = label_folder / target_name

    try:
        with target_path.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    finally:
        upload_file.file.close()

    return target_path


def append_csv_log(labels_csv: Path, filename: str, trust_label: TrustLabel) -> None:
    """
    Append a new row to labels.csv with filename and trust label.
    Assumes file and header exist (handled by ensure_directories_and_csv).
    """
    try:
        with labels_csv.open(mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([filename, trust_label])
    except Exception as e:
        # Logging CSV failure but not failing the whole request
        # to avoid losing the saved image if CSV append fails.
        print(f"Warning: failed to append to labels.csv: {e}")


@router.post("/upload-image")
async def upload_labeled_image(
    file: UploadFile = File(...),
    trust_label: str = Form(..., description='One of: "high", "medium", "low"'),
):
    """
    Upload a labeled image into the internal visual dataset.

    - Accepts multipart/form-data.
    - Validates trust_label against allowed values.
    - Saves the file to dataset/images/<label_folder>/ with a timestamped filename.
    - Appends a row to dataset/labels.csv.
    """
    normalized_label = trust_label.strip().lower()
    allowed_labels: list[TrustLabel] = ["high", "medium", "low"]

    if normalized_label not in allowed_labels:
        raise HTTPException(
            status_code=400,
            detail=f'Invalid trust_label "{trust_label}". Must be one of: "high", "medium", "low".',
        )

    try:
        label_folder, labels_csv = get_dataset_paths(normalized_label)  # type: ignore[arg-type]
        ensure_directories_and_csv(label_folder, labels_csv)

        saved_path = save_uploaded_file(label_folder, file)

        # Log to CSV (filename relative to dataset/images for portability)
        relative_filename = saved_path.name
        append_csv_log(labels_csv, relative_filename, normalized_label)  # type: ignore[arg-type]

        # Return JSON response
        project_root = get_project_root()
        relative_path = saved_path.relative_to(project_root)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "path": str(relative_path),
                "label": normalized_label,
            },
        )
    except HTTPException:
        # Re-raise HTTP exceptions directly
        raise
    except Exception as e:
        # Catch-all for any unexpected error
        raise HTTPException(status_code=500, detail=f"Unexpected error while processing upload: {e}")


