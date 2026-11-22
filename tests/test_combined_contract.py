import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class CombinedBaselineTests(unittest.TestCase):
    def test_frozen_research_is_unchanged(self):
        hashes = json.loads((ROOT / 'tests/fixtures/combined/frozen-research-hashes.json').read_text())
        for name, expected in hashes.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)

    def test_connection_fixture_is_real_public_commit(self):
        value = json.loads((ROOT / 'tests/fixtures/combined/public-repository-connection.json').read_text())
        self.assertEqual(value['connection_status'], 'connected')
        row = value['commit_analysis']
        self.assertEqual(row['repository'], 'janithush/CI-CD-Build-Failure-Prediction')
        self.assertEqual(row['commit_id'], 'ae420f5e361c7f0d16f2224f1934ac894d8a6e71')
        self.assertGreater(row['files_changed'], 0)
        self.assertNotIn('github_token', row)

    def test_legacy_controls_are_preserved(self):
        source = (ROOT / 'dashboard/index.html').read_text()
        for name in ['connectBtn', 'predictBtn', 'changeRepoBtn', 'copyShaBtn', 'feedbackBtn']:
            self.assertIn('id="' + name + '"', source)
        for name in ['previousHistoryPage', 'nextHistoryPage', 'loadHistory']:
            self.assertIn(name, source)

if __name__ == '__main__':
    unittest.main()
