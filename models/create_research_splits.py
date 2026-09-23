"""Create chronological train/validation/test manifests without commit overlap."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "processed" / "research_features.csv"
DEFAULT_CONFIG = ROOT / "configs" / "research.json"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "research_split_manifest.csv"


def create_splits(data: pd.DataFrame, train_fraction: float, validation_fraction: float) -> pd.DataFrame:
    required = {"repository", "commit_id", "run_id", "run_attempt", "run_started_at"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    work = data.copy()
    work["run_started_at"] = pd.to_datetime(work["run_started_at"], utc=True)
    work["group_id"] = work["repository"].astype(str) + "::" + work["commit_id"].astype(str)
    groups = (
        work.groupby("group_id", as_index=False)["run_started_at"]
        .min()
        .sort_values(["run_started_at", "group_id"])
        .reset_index(drop=True)
    )
    count = len(groups)
    train_end = max(1, int(count * train_fraction))
    validation_end = max(train_end + 1, int(count * (train_fraction + validation_fraction)))
    validation_end = min(validation_end, count)
    groups["split"] = "test"
    groups.loc[: train_end - 1, "split"] = "train"
    if validation_end > train_end:
        groups.loc[train_end : validation_end - 1, "split"] = "validation"
    manifest = work.merge(groups[["group_id", "split"]], on="group_id", how="left")
    overlap = 0
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        a = set(manifest.loc[manifest["split"].eq(left), "group_id"])
        b = set(manifest.loc[manifest["split"].eq(right), "group_id"])
        overlap += len(a & b)
    if overlap:
        raise AssertionError(f"Detected {overlap} group overlaps between splits")
    return manifest[["repository", "commit_id", "run_id", "run_attempt", "group_id", "split"]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    fractions = config["splits"]
    data = pd.read_csv(args.input)
    manifest = create_splits(
        data,
        fractions["train_fraction"],
        fractions["validation_fraction"],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(args.output, index=False)
    print(manifest["split"].value_counts().to_string())
    print(f"Commit-group overlap: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
