"""Strict-availability variant of build_research_features.py.

Repair: a prior run's outcome enters a row's history ONLY when its
outcome_available_at is strictly earlier than that row's run_started_at.

outcome_available_at uses workflow_runs.updated_at unchanged. This is a
retrospective recorded-timestamp proxy, not a provider guarantee of exact job
completion. A prior sample found updated_at at or after the last returned job
completion in 173 complete samples, but does not certify every dataset row.
Late retention updates delay usable history. No duration imputation is used
in the primary recorded mode. Genuine prediction-time observability and
unobserved timestamp errors remain limitations.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "research" / "buildrisk.sqlite3"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "research_features_strict.csv"
DEFAULT_CONFIG = ROOT / "configs" / "research.json"

# Reuse the original module's static pieces so file aggregation stays identical.
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "orig_brf", str(Path(__file__).with_name("build_research_features.py"))
)
_orig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_orig)
load_tables = _orig.load_tables
aggregate_files = _orig.aggregate_files
enforce_eligibility = _orig.enforce_eligibility


def strict_group_history(
    starts: np.ndarray,      # run_started_at (ns) for rows in this group, row order
    avails: np.ndarray,      # outcome_available_at (ns) for rows in this group, row order
    results: np.ndarray,     # build_result for rows in this group, row order
) -> dict[str, np.ndarray]:
    """For each row, aggregate history over rows with avail < own start."""
    n = len(starts)
    missing_ns = np.iinfo(np.int64).min
    if len(avails) != n or len(results) != n:
        raise ValueError('History input arrays must have the same length')
    if np.any(starts == missing_ns) or np.any(avails == missing_ns):
        raise ValueError('Missing history timestamps must be withheld or rejected before feature building')
    if np.any(avails < starts):
        raise ValueError('An outcome cannot become available before its own run starts')
    order = np.argsort(avails, kind="mergesort")  # availability order
    s_avail = avails[order]
    s_start = starts[order]
    s_res = results[order].astype(float)

    cum_res = np.concatenate([[0.0], np.cumsum(s_res)])
    fail_start = np.where(s_res == 1.0, s_start, np.nan)
    # forward-fill last failure start in availability order
    last_fail = np.full(n, np.nan)
    cur = np.nan
    for i in range(n):
        if not np.isnan(fail_start[i]):
            cur = fail_start[i]
        last_fail[i] = cur

    windows = (3, 5, 10, 20)
    roll = {}
    for w in windows:
        r = np.full(n, np.nan)
        cs = cum_res
        for i in range(n):
            lo = max(0, i - w + 1)
            r[i] = (cs[i + 1] - cs[lo]) / (i - lo + 1)
        roll[w] = r

    out = {
        "prior_runs": np.zeros(n, dtype=float),
        "previous_result": np.full(n, np.nan),
        "prior_failure_rate": np.full(n, np.nan),
        "previous_started_at": np.full(n, np.nan),
        "hours_since_previous_failure": np.full(n, np.nan),
        "excluded_inflight": np.zeros(n, dtype=float),
    }
    for w in windows:
        out[f"failure_rate_{w}"] = np.full(n, np.nan)

    # number of earlier-started runs per row (for excluded_inflight)
    start_order = np.argsort(starts, kind="mergesort")
    s_starts_sorted = starts[start_order]

    for i in range(n):
        own_start = starts[i]
        k = int(np.searchsorted(s_avail, own_start, side="left"))  # avail < own_start
        earlier_started = int(np.searchsorted(s_starts_sorted, own_start, side="left"))
        out["excluded_inflight"][i] = max(0, earlier_started - k)
        out["prior_runs"][i] = k
        if k > 0:
            j = k - 1
            out["previous_result"][i] = s_res[j]
            out["prior_failure_rate"][i] = cum_res[k] / k
            out["previous_started_at"][i] = s_start[j]
            if not np.isnan(last_fail[j]):
                out["hours_since_previous_failure"][i] = (
                    own_start - last_fail[j]
                ) / 3.6e12
            for w in windows:
                out[f"failure_rate_{w}"][i] = roll[w][j]
    return out


def add_strict_history_features(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["run_started_at"] = pd.to_datetime(data["run_started_at"], utc=True)
    data["outcome_available_at"] = pd.to_datetime(data["outcome_available_at"], utc=True)
    data["build_result"] = data["conclusion"].eq("failure").astype(int)

    specs = [
        ("workflow", ["repository", "workflow_id"], {
            "prior_runs": "workflow_prior_runs",
            "previous_result": "previous_workflow_result",
            "prior_failure_rate": "workflow_prior_failure_rate",
            "previous_started_at": "previous_workflow_started_at",
            "hours_since_previous_failure": "hours_since_previous_failure",
            "excluded_inflight": "workflow_excluded_inflight",
            "failure_rate_3": "workflow_failure_rate_3",
            "failure_rate_5": "workflow_failure_rate_5",
            "failure_rate_10": "workflow_failure_rate_10",
            "failure_rate_20": "workflow_failure_rate_20",
        }),
        ("repository", ["repository"], {
            "prior_runs": "repository_prior_runs",
            "prior_failure_rate": "repository_prior_failure_rate",
        }),
        ("branch", ["repository", "branch"], {
            "prior_failure_rate": "branch_prior_failure_rate",
        }),
    ]
    ns_start = (data["run_started_at"].astype("int64")).to_numpy()
    ns_avail = (data["outcome_available_at"].astype("int64")).to_numpy()
    res = data["build_result"].to_numpy()

    data["workflow_excluded_inflight"] = 0.0
    for name, keys, mapping in specs:
        cols = {v: np.full(len(data), np.nan) for v in mapping.values()}
        for _, idx in data.groupby(keys).indices.items():
            idx = np.asarray(idx)
            h = strict_group_history(ns_start[idx], ns_avail[idx], res[idx])
            for src, dst in mapping.items():
                cols[dst][idx] = h[src]
        for dst, arr in cols.items():
            data[dst] = arr

    data["hours_since_previous_workflow_run"] = (
        data["run_started_at"]
        - pd.to_datetime(data["previous_workflow_started_at"], utc=True)
    ).dt.total_seconds() / 3600
    data["commit_hour_utc"] = data["run_started_at"].dt.hour
    data["commit_day_of_week"] = data["run_started_at"].dt.dayofweek
    data["is_weekend"] = data["commit_day_of_week"].isin([5, 6]).astype(int)
    data["total_changes"] = data["lines_added"].fillna(0) + data["lines_deleted"].fillna(0)
    data["churn_per_file"] = data["total_changes"] / data["files_changed"].clip(lower=1)
    return data


def build_features(database: Path, config_path: Path, enforce: bool, availability_mode: str = "recorded") -> pd.DataFrame:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    with sqlite3.connect(database) as connection:
        runs, files = load_tables(connection)
        avail = pd.read_sql_query(
            "SELECT repository, run_id, run_attempt, workflow_id, run_started_at, "
            "updated_at AS outcome_available_at FROM workflow_runs",
            connection,
        )
    # Primary mode preserves recorded updated_at, including late bumps.
    # A >24-hour duration is a sensitivity flag, not proof of a bad timestamp.
    # Neither recorded mode nor the limited job sample certifies dataset-wide
    # completion timing. exclude_bumped and median are legacy sensitivities;
    # median imputes completion and is not used for this approved comparison.
    avail["run_started_at"] = pd.to_datetime(avail["run_started_at"], utc=True)
    avail["outcome_available_at"] = pd.to_datetime(avail["outcome_available_at"], utc=True)
    duration = avail["outcome_available_at"] - avail["run_started_at"]
    bump = duration > pd.Timedelta(hours=24)
    avail["availability_imputed"] = 0
    if availability_mode == "exclude_bumped":
        avail.loc[bump[bump].index, "outcome_available_at"] = pd.Timestamp("2262-01-01", tz="UTC")
    elif availability_mode == "median":
        med = (avail.loc[~bump]
               .groupby(["repository", "workflow_id"])
               .apply(lambda g: (g["outcome_available_at"] - g["run_started_at"]).median(),
                      include_groups=False)
               .rename("median_duration"))
        avail = avail.merge(med, on=["repository", "workflow_id"], how="left")
        avail.loc[bump[bump].index, "availability_imputed"] = 1
        avail.loc[bump[bump].index, "outcome_available_at"] = (
            avail.loc[bump[bump].index, "run_started_at"]
            + avail.loc[bump[bump].index, "median_duration"]
        )
        avail = avail.drop(columns=["median_duration"])
    data = runs.merge(aggregate_files(files), on=["repository", "commit_id"], how="left")
    data = data.merge(avail[["repository", "run_id", "run_attempt", "outcome_available_at", "availability_imputed"]],
                      on=["repository", "run_id", "run_attempt"], how="left", validate="one_to_one")
    count_columns = [
        "dependency_files_changed", "test_files_changed", "workflow_files_changed",
        "source_files_changed", "config_files_changed", "file_extension_count",
        "files_added", "files_removed", "files_renamed",
    ]
    data[count_columns] = data[count_columns].fillna(0).astype(int)
    excluded = "|".join(config["dataset"]["excluded_workflow_keywords"])
    if excluded:
        data = data[~data["workflow_name"].fillna("").str.lower().str.contains(excluded, regex=True)]
    data = add_strict_history_features(data)
    if enforce:
        data = enforce_eligibility(data, config)
    return data.replace([np.inf, -np.inf], np.nan)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-ineligible-repositories", action="store_true")
    parser.add_argument("--availability-mode", choices=["recorded", "exclude_bumped", "median"], default="recorded")
    args = parser.parse_args()
    data = build_features(
        args.database.resolve(), args.config.resolve(), not args.allow_ineligible_repositories,
        availability_mode=args.availability_mode,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(args.output, index=False)
    print(f"Wrote {len(data):,} workflow-run observations to {args.output}")
    print(f"Failures: {int(data['build_result'].sum()) if len(data) else 0}")
    affected = (data["workflow_excluded_inflight"] > 0).sum()
    print(f"Rows with at least one in-flight run excluded from workflow history: {affected:,}")
    unknown_prev = data["previous_workflow_result"].isna().sum()
    print(f"Rows with unknown previous workflow result (no available prior outcome): {unknown_prev:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
