"""
CLI utility to create OpenAI fine-tune JSONL for landing friction dataset.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _prepare_import_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def main(force_rebuild: bool = False) -> None:
    _prepare_import_path()
    from landing_friction.pipeline import prepare_landing_friction_finetune

    result = prepare_landing_friction_finetune(force_rebuild=force_rebuild)
    print("✅ Fine-tune JSONL prepared")
    print(f"Examples written: {result.dataset_examples}")
    print(f"Output path: {result.output_path}")
    if result.dataset_summary:
        print("Dataset summary:")
        print(f"  Total samples: {result.dataset_summary.total_samples}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare landing friction fine-tune JSONL.")
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Rebuild the merged dataset before preparing the JSONL file.",
    )
    args = parser.parse_args()
    main(force_rebuild=args.force_rebuild)







