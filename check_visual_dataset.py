"""
Visual Trust Dataset Checker
============================

Simple script to count images in the training_data/images/ folder structure.

Usage:
    python check_visual_dataset.py

Expected structure:
    training_data/
      images/
        low/
        medium/
        high/
"""

from pathlib import Path


def count_images_in_folder(folder: Path) -> int:
    """
    Count image files in a folder.
    Supports: .jpg, .jpeg, .png, .webp
    """
    if not folder.exists() or not folder.is_dir():
        return 0

    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    count = 0
    for file_path in folder.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            count += 1
    return count


def main():
    """Main entry point for the dataset checker."""
    # Base folder: training_data/images
    base_folder = Path("training_data") / "images"

    if not base_folder.exists():
        print(f"Error: Dataset folder not found: {base_folder}")
        print("Expected structure: training_data/images/{low,medium,high}/")
        return

    # Subfolders to check
    subfolders = ["low", "medium", "high"]
    results = {}

    print("Visual Trust Dataset Summary:\n")

    for subfolder_name in subfolders:
        subfolder_path = base_folder / subfolder_name
        if not subfolder_path.exists():
            print(f"  - {subfolder_name}: folder NOT FOUND")
            results[subfolder_name] = None
        else:
            count = count_images_in_folder(subfolder_path)
            print(f"  - {subfolder_name}: {count} images")
            results[subfolder_name] = count

    # Calculate total
    total = sum(count for count in results.values() if count is not None)
    print(f"\n  Total images: {total}")


if __name__ == "__main__":
    main()

