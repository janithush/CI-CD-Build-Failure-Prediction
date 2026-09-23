import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from dataset_collector.github_actions_research_collector import (
    Collector,
    file_extension,
    load_repositories,
    load_or_create_salt,
    pseudonym,
)
from models.create_research_splits import create_splits
from preprocessing.build_research_features import add_history_features
from preprocessing.validate_research_dataset import validate_database


class CollectorFoundationTests(unittest.TestCase):
    def test_pseudonym_is_stable_and_namespaced(self):
        first = pseudonym("developer", "salt", "owner/repo")
        self.assertEqual(first, pseudonym("developer", "salt", "owner/repo"))
        self.assertNotEqual(first, pseudonym("developer", "salt", "other/repo"))
        self.assertNotIn("developer", first)

    def test_file_extensions(self):
        self.assertEqual(file_extension("src/main.py"), ".py")
        self.assertEqual(file_extension(".github/workflows/ci.yml"), ".yml")
        self.assertEqual(file_extension(".env"), ".env")

    def test_repository_list_is_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "repositories.txt"
            path.write_text("# note\na/b\na/b\nc/d\n", encoding="utf-8")
            self.assertEqual(load_repositories(path), ["a/b", "c/d"])

    def test_hash_salt_is_created_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".hash_salt"
            first = load_or_create_salt(path)
            self.assertEqual(first, load_or_create_salt(path))
            self.assertGreaterEqual(len(first), 64)

    def test_empty_database_schema_validates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "research.sqlite3"
            collector = Collector(path, None, "salt", datetime.now(timezone.utc))
            collector.close()
            result = validate_database(path)
            self.assertTrue(result["valid"])
            self.assertEqual(result["runs"], 0)


class LeakagePreventionTests(unittest.TestCase):
    def sample_runs(self):
        return pd.DataFrame(
            {
                "repository": ["a/r", "a/r", "a/r", "b/r"],
                "workflow_id": [1, 1, 1, 2],
                "commit_id": ["c1", "c2", "c3", "c4"],
                "run_id": [1, 2, 3, 4],
                "run_attempt": [1, 1, 1, 1],
                "run_started_at": [
                    "2025-01-01T00:00:00Z",
                    "2025-01-02T00:00:00Z",
                    "2025-01-03T00:00:00Z",
                    "2025-01-04T00:00:00Z",
                ],
                "conclusion": ["success", "failure", "success", "failure"],
                "branch": ["main", "main", "main", "main"],
                "lines_added": [1, 2, 3, 4],
                "lines_deleted": [0, 0, 1, 1],
                "files_changed": [1, 1, 2, 2],
            }
        )

    def test_history_uses_only_prior_outcomes(self):
        result = add_history_features(self.sample_runs())
        repo_a = result[result["repository"].eq("a/r")].reset_index(drop=True)
        self.assertTrue(pd.isna(repo_a.loc[0, "previous_workflow_result"]))
        self.assertEqual(repo_a.loc[1, "previous_workflow_result"], 0)
        self.assertEqual(repo_a.loc[2, "previous_workflow_result"], 1)
        self.assertEqual(repo_a.loc[1, "workflow_prior_failure_rate"], 0)
        self.assertEqual(repo_a.loc[2, "workflow_prior_failure_rate"], 0.5)

    def test_commit_group_never_crosses_splits(self):
        data = pd.concat(
            [self.sample_runs(), self.sample_runs().assign(run_id=[5, 6, 7, 8])],
            ignore_index=True,
        )
        manifest = create_splits(data, 0.5, 0.25)
        per_group = manifest.groupby("group_id")["split"].nunique()
        self.assertEqual(per_group.max(), 1)


if __name__ == "__main__":
    unittest.main()
