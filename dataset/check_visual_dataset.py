"""
Small helper script to inspect the local visual trust dataset.

Usage:
    python dataset/check_visual_dataset.py

It scans dataset/images/ and counts how many image files exist in:
    - high_trust/
    - medium_trust/
    - low_trust/

This does NOT modify any files or call external APIs.
"""

from pathlib import Path


def count_images_in_folder(folder: Path) -> int:
    """
    Count image-like files in a folder.
    This is a lightweight heuristic based on file extensions.
    """
    if not folder.exists():
        return 0

    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    count = 0
    for path in folder.iterdir():
        if path.is_file() and path.suffix.lower() in image_exts:
            count += 1
    return count


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    dataset_root = project_root / "dataset" / "images"

    # Ensure base folders exist (non-destructive: just mkdir if missing)
    high_dir = dataset_root / "high_trust"
    med_dir = dataset_root / "medium_trust"
    low_dir = dataset_root / "low_trust"

    for d in (dataset_root, high_dir, med_dir, low_dir):
        d.mkdir(parents=True, exist_ok=True)

    high_count = count_images_in_folder(high_dir)
    med_count = count_images_in_folder(med_dir)
    low_count = count_images_in_folder(low_dir)

    print("Visual Trust Dataset Summary:")
    print(f"  high_trust:   {high_count} images")
    print(f"  medium_trust: {med_count} images")
    print(f"  low_trust:    {low_count} images")


if __name__ == "__main__":
    main()


