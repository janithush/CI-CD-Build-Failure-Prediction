"""Validate workflow-run research data before feature engineering or training."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "research" / "buildrisk.sqlite3"


def scalar(connection: sqlite3.Connection, query: str) -> int:
    return int(connection.execute(query).fetchone()[0])


def validate_database(database: Path) -> dict:
    if not database.exists():
        raise FileNotFoundError(f"Research database not found: {database}")

    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        required = {
            "repositories",
            "commits",
            "changed_files",
            "workflows",
            "workflow_runs",
            "workflow_jobs",
        }
        missing_tables = sorted(required - tables)
        if missing_tables:
            return {"valid": False, "missing_tables": missing_tables}

        summary = {
            "repositories": scalar(connection, "SELECT COUNT(*) FROM repositories"),
            "runs": scalar(connection, "SELECT COUNT(*) FROM workflow_runs"),
            "commits": scalar(connection, "SELECT COUNT(*) FROM commits"),
            "workflows": scalar(connection, "SELECT COUNT(*) FROM workflows"),
            "jobs": scalar(connection, "SELECT COUNT(*) FROM workflow_jobs"),
            "completed_binary_runs": scalar(
                connection,
                "SELECT COUNT(*) FROM workflow_runs "
                "WHERE conclusion IN ('success', 'failure')",
            ),
            "failures": scalar(
                connection,
                "SELECT COUNT(*) FROM workflow_runs WHERE conclusion='failure'",
            ),
            "missing_commit_ids": scalar(
                connection,
                "SELECT COUNT(*) FROM workflow_runs "
                "WHERE commit_id IS NULL OR TRIM(commit_id)=''",
            ),
            "duplicate_run_keys": scalar(
                connection,
                "SELECT COUNT(*) FROM ("
                "SELECT repository, run_id, run_attempt FROM workflow_runs "
                "GROUP BY repository, run_id, run_attempt HAVING COUNT(*) > 1)",
            ),
            "orphan_jobs": scalar(
                connection,
                "SELECT COUNT(*) FROM workflow_jobs j LEFT JOIN workflow_runs r "
                "ON r.repository=j.repository AND r.run_id=j.run_id "
                "AND r.run_attempt=j.run_attempt WHERE r.run_id IS NULL",
            ),
            "future_or_equal_commits": scalar(
                connection,
                "SELECT COUNT(*) FROM workflow_runs r JOIN commits c "
                "ON c.repository=r.repository AND c.commit_id=r.commit_id "
                "WHERE c.commit_date IS NOT NULL AND r.run_started_at IS NOT NULL "
                "AND c.commit_date > r.run_started_at",
            ),
        }
    finally:
        connection.close()

    violations = {
        key: summary[key]
        for key in (
            "missing_commit_ids",
            "duplicate_run_keys",
            "orphan_jobs",
            "future_or_equal_commits",
        )
        if summary[key] > 0
    }
    summary["valid"] = not violations
    summary["violations"] = violations
    if summary["completed_binary_runs"]:
        summary["failure_rate"] = round(
            summary["failures"] / summary["completed_binary_runs"], 6
        )
    else:
        summary["failure_rate"] = None
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    try:
        result = validate_database(args.database.resolve())
    except (FileNotFoundError, sqlite3.DatabaseError) as error:
        print(json.dumps({"valid": False, "error": str(error)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    sys.exit(main())
