"""
CLI utility to merge labeled landing friction samples into a dataset.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _prepare_import_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def main() -> None:
    _prepare_import_path()
    from landing_friction.pipeline import build_landing_friction_dataset

    result = build_landing_friction_dataset()
    print("✅ Landing friction dataset built")
    print(f"Total samples: {result.total_samples}")
    print("Counts by label:")
    for label, count in result.counts_by_label.items():
        print(f"  - {label}: {count}")
    print("Average total friction by label:")
    for label, average in result.average_total_friction.items():
        print(f"  - {label}: {average}")
    if result.invalid_files:
        print("⚠️ Invalid files skipped:")
        for path in result.invalid_files:
            print(f"  - {path}")
    print(f"Dataset path: {result.output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build landing friction dataset.")
    _ = parser.parse_args()
    main()







