"""Build a leakage-safe, workflow-run-level model table from normalized data."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "research" / "buildrisk.sqlite3"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "research_features.csv"
DEFAULT_CONFIG = ROOT / "configs" / "research.json"

DEPENDENCY_NAMES = {
    "requirements.txt", "package.json", "package-lock.json", "yarn.lock",
    "pnpm-lock.yaml", "pom.xml", "build.gradle", "build.gradle.kts",
    "composer.json", "pyproject.toml", "poetry.lock", "go.mod", "go.sum",
    "cargo.toml", "cargo.lock", "environment.yml",
}
SOURCE_EXTENSIONS = {
    ".py", ".java", ".kt", ".kts", ".js", ".jsx", ".ts", ".tsx",
    ".go", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php",
    ".rs", ".swift", ".scala",
}


def load_tables(connection: sqlite3.Connection) -> tuple[pd.DataFrame, pd.DataFrame]:
    runs = pd.read_sql_query(
        "SELECT r.*, p.primary_language FROM workflow_runs r "
        "JOIN repositories p ON p.repository=r.repository "
        "WHERE r.conclusion IN ('success', 'failure') "
        "AND r.commit_id IS NOT NULL AND r.run_started_at IS NOT NULL",
        connection,
    )
    commits = pd.read_sql_query(
        "SELECT * FROM commits",
        connection,
    )
    files = pd.read_sql_query(
        "SELECT repository, commit_id, filename, extension, change_status "
        "FROM changed_files",
        connection,
    )
    merged = runs.merge(commits, on=["repository", "commit_id"], how="inner")
    if "commit_date" in merged.columns and "run_started_at" in merged.columns:
        valid_time_mask = (
            merged["commit_date"].isna()
            | merged["run_started_at"].isna()
            | (merged["commit_date"] <= merged["run_started_at"])
        )
        merged = merged[valid_time_mask].reset_index(drop=True)
    return merged, files


def aggregate_files(files: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "repository", "commit_id", "dependency_files_changed", "test_files_changed",
        "workflow_files_changed", "source_files_changed", "config_files_changed",
        "file_extension_count", "files_added", "files_removed", "files_renamed",
    ]
    if files.empty:
        return pd.DataFrame(columns=columns)
    work = files.copy()
    normalized = work["filename"].str.replace("\\", "/", regex=False).str.lower()
    basename = normalized.str.rsplit("/", n=1).str[-1]
    work["dependency_files_changed"] = basename.isin(DEPENDENCY_NAMES).astype(int)
    work["test_files_changed"] = normalized.str.contains(
        r"(?:^|/)(?:tests?|specs?)(?:/|$)|(?:^|[_\-.])(?:test|spec)(?:[_\-.]|$)", regex=True
    ).astype(int)
    work["workflow_files_changed"] = normalized.str.startswith(".github/workflows/").astype(int)
    work["source_files_changed"] = work["extension"].str.lower().isin(SOURCE_EXTENSIONS).astype(int)
    work["config_files_changed"] = normalized.str.contains(
        r"(?:^|/)(?:config|configs)(?:/|$)|dockerfile|docker-compose|\.env|settings", regex=True
    ).astype(int)
    work["files_added"] = work["change_status"].eq("added").astype(int)
    work["files_removed"] = work["change_status"].eq("removed").astype(int)
    work["files_renamed"] = work["change_status"].eq("renamed").astype(int)
    aggregated = work.groupby(["repository", "commit_id"], as_index=False).agg(
        dependency_files_changed=("dependency_files_changed", "sum"),
        test_files_changed=("test_files_changed", "sum"),
        workflow_files_changed=("workflow_files_changed", "sum"),
        source_files_changed=("source_files_changed", "sum"),
        config_files_changed=("config_files_changed", "sum"),
        file_extension_count=("extension", "nunique"),
        files_added=("files_added", "sum"),
        files_removed=("files_removed", "sum"),
        files_renamed=("files_renamed", "sum"),
    )
    return aggregated[columns]


def prior_expanding_mean(values: pd.Series) -> pd.Series:
    return values.shift(1).expanding().mean()


def add_history_features(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.sort_values(["run_started_at", "repository", "run_id", "run_attempt"]).copy()
    data["build_result"] = data["conclusion"].eq("failure").astype(int)
    workflow_key = ["repository", "workflow_id"]
    repo_key = ["repository"]
    branch_key = ["repository", "branch"]

    data["workflow_prior_runs"] = data.groupby(workflow_key).cumcount()
    data["repository_prior_runs"] = data.groupby(repo_key).cumcount()
    data["previous_workflow_result"] = data.groupby(workflow_key)["build_result"].shift(1)
    data["workflow_prior_failure_rate"] = data.groupby(workflow_key, group_keys=False)[
        "build_result"
    ].apply(prior_expanding_mean)
    data["repository_prior_failure_rate"] = data.groupby(repo_key, group_keys=False)[
        "build_result"
    ].apply(prior_expanding_mean)
    data["branch_prior_failure_rate"] = data.groupby(branch_key, group_keys=False)[
        "build_result"
    ].apply(prior_expanding_mean)
    for window in (3, 5, 10, 20):
        data[f"workflow_failure_rate_{window}"] = data.groupby(
            workflow_key, group_keys=False
        )["build_result"].apply(
            lambda values, size=window: values.shift(1).rolling(size, min_periods=1).mean()
        )

    data["run_started_at"] = pd.to_datetime(data["run_started_at"], utc=True)
    data["previous_workflow_started_at"] = data.groupby(workflow_key)["run_started_at"].shift(1)
    data["hours_since_previous_workflow_run"] = (
        data["run_started_at"] - data["previous_workflow_started_at"]
    ).dt.total_seconds() / 3600

    failure_time = data["run_started_at"].where(data["build_result"].eq(1))
    previous_failure_time = failure_time.groupby(
        [data["repository"], data["workflow_id"]]
    ).ffill().groupby([data["repository"], data["workflow_id"]]).shift(1)
    data["hours_since_previous_failure"] = (
        data["run_started_at"] - previous_failure_time
    ).dt.total_seconds() / 3600

    data["commit_hour_utc"] = data["run_started_at"].dt.hour
    data["commit_day_of_week"] = data["run_started_at"].dt.dayofweek
    data["is_weekend"] = data["commit_day_of_week"].isin([5, 6]).astype(int)
    data["total_changes"] = data["lines_added"].fillna(0) + data["lines_deleted"].fillna(0)
    data["churn_per_file"] = data["total_changes"] / data["files_changed"].clip(lower=1)
    return data


def enforce_eligibility(data: pd.DataFrame, config: dict) -> pd.DataFrame:
    minimum_runs = config["dataset"]["minimum_completed_runs_per_repository"]
    minimum_failures = config["dataset"]["minimum_failures_per_repository"]
    stats = data.groupby("repository")["build_result"].agg(["size", "sum"])
    eligible = stats.index[(stats["size"] >= minimum_runs) & (stats["sum"] >= minimum_failures)]
    return data[data["repository"].isin(eligible)].copy()


def build_features(database: Path, config_path: Path, enforce: bool) -> pd.DataFrame:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    with sqlite3.connect(database) as connection:
        runs, files = load_tables(connection)
    data = runs.merge(aggregate_files(files), on=["repository", "commit_id"], how="left")
    count_columns = [
        "dependency_files_changed", "test_files_changed", "workflow_files_changed",
        "source_files_changed", "config_files_changed", "file_extension_count",
        "files_added", "files_removed", "files_renamed",
    ]
    data[count_columns] = data[count_columns].fillna(0).astype(int)
    excluded = "|".join(config["dataset"]["excluded_workflow_keywords"])
    if excluded:
        data = data[~data["workflow_name"].fillna("").str.lower().str.contains(excluded, regex=True)]
    data = add_history_features(data)
    if enforce:
        data = enforce_eligibility(data, config)
    return data.replace([np.inf, -np.inf], np.nan)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-ineligible-repositories", action="store_true")
    args = parser.parse_args()
    data = build_features(
        args.database.resolve(), args.config.resolve(), not args.allow_ineligible_repositories
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(args.output, index=False)
    print(f"Wrote {len(data):,} workflow-run observations to {args.output}")
    print(f"Repositories: {data['repository'].nunique() if len(data) else 0}")
    print(f"Failures: {int(data['build_result'].sum()) if len(data) else 0}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
