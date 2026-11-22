import json
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from api import risk_analyzer as risk
ROOT = Path(__file__).resolve().parents[1]

class ProbabilityAdviceTests(unittest.TestCase):
    def test_real_public_commit_preserves_exact_raw_output(self):
        row = json.loads((ROOT / 'tests/fixtures/combined/public-repository-connection.json').read_text())['commit_analysis']
        if risk._runtime_mismatches:
            with self.assertRaisesRegex(RuntimeError, 'Prediction disabled'):
                risk.predict_build_risk(row)
            return
        expected = float(risk._model.predict_proba(risk.build_research_features(row))[0][1]) * 100
        result = risk.predict_build_risk(row)
        self.assertAlmostEqual(result['ml_failure_probability'], expected, places=12)
        self.assertAlmostEqual(result['raw_model_probability'], expected, places=12)
        self.assertEqual(result['advisory_risk_score'], result['final_failure_risk_score'])
        self.assertEqual(len(result['model_info']['artifact_sha256']), 64)

    def test_controlled_high_rules_do_not_mutate_probability(self):
        # Deliberate unit-test response, not a real provider or scientific result.
        class Model:
            def predict_proba(self, frame): return np.array([[0.98, 0.02]])
        row = {'commit_id': 'controlled-unit-test', 'previous_build_status': 'failure', 'dependency_file_changed': 1}
        with patch.object(risk, '_model', Model()), patch.object(risk, '_runtime_mismatches', []):
            result = risk.predict_build_risk(row)
        self.assertEqual(result['raw_model_probability'], 2.0)
        self.assertEqual(result['ml_failure_probability'], 2.0)
        self.assertTrue(result['advice_adjusted'])
        self.assertGreater(result['advisory_risk_score'], 2.0)
        self.assertFalse(any('exceeds' in reason for reason in result['reasons']))
        self.assertTrue(any('below' in reason for reason in result['reasons']))

if __name__ == '__main__': unittest.main()
