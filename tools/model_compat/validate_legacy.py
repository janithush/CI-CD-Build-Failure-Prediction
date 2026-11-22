"""Verify the portable evaluator against a fingerprint-checked original object.

Use Python >=3.11 with sklearn 1.9.1 for the recorded-version reference.
The portable-only path verifies separately against that saved reference output.
No fitting, artifact editing or version relabeling is performed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import sys
import warnings
import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.exceptions import InconsistentVersionWarning

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from api.portable_legacy import PortableLegacy


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validation_inputs(portable):
    source = ROOT / 'data/processed/research_features.csv'
    frame = pd.read_csv(source, dtype={'workflow_id': str})[portable.features]
    stress = frame.sample(n=512, random_state=17).copy().reset_index(drop=True)
    for i, name in enumerate(portable.numeric):
        values = stress[name].to_numpy(float)
        values[i::17] = np.nan
        values[2::29] = 1e9
        values[3::31] = -1e6
        stress[name] = values
    for name in portable.categorical:
        stress[name] = stress[name].astype(object)
        stress.loc[::13, name] = 'unseen-controlled-category'
        stress.loc[1::19, name] = np.nan
    return frame, stress, digest(source)


def validate(reference_output=None, portable_only_reference=None):
    path = ROOT / 'models/compatible/legacy_rf_sigmoid_v1.json'
    portable = PortableLegacy(path)
    frame, stress, data_sha = validation_inputs(portable)
    source_path = ROOT / portable.manifest['source_file']
    if digest(source_path) != portable.manifest['source_sha256']:
        raise ValueError('Original artifact fingerprint does not match reviewed source')
    runtime = dict(python=platform.python_version(), sklearn=sklearn.__version__,
                   numpy=np.__version__, pandas=pd.__version__, scipy=scipy.__version__,
                   joblib=joblib.__version__)
    version_warnings = []
    if portable_only_reference:
        metadata_path = Path(portable_only_reference).with_suffix('.json')
        metadata = json.loads(metadata_path.read_text())
        assert metadata['recorded_version_reference'] is True
        assert metadata['input_data_sha256'] == data_sha
        assert metadata['source_artifact_sha256'] == digest(source_path)
        assert metadata['reference_arrays_sha256'] == digest(Path(portable_only_reference))
        with np.load(portable_only_reference, allow_pickle=False) as reference:
            a = reference['source_probability'].copy()
            stress_a = reference['stress_probability'].copy()
            expected_transform = reference['transformed_first256'].copy()
        reference_runtime = metadata['reference_runtime']
        matched = True
        repr_ok = metadata['original_representation_ok']
    else:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always', InconsistentVersionWarning)
            original = joblib.load(source_path)['model']
        version_warnings = sorted({w.message.original_sklearn_version for w in caught
                                   if isinstance(w.message, InconsistentVersionWarning)})
        matched = portable.manifest['source_reported_sklearn'] == [sklearn.__version__] and not version_warnings
        try:
            repr(original)
            repr_ok = True
        except Exception:
            repr_ok = False
        a = np.concatenate([original.predict_proba(frame.iloc[i:i+256])[:, 1]
                            for i in range(0, len(frame), 256)])
        stress_a = original.predict_proba(stress)[:, 1]
        expected_transform = original.estimator.estimator.steps[0][1].transform(frame.iloc[:256])
        if hasattr(expected_transform, 'toarray'):
            expected_transform = expected_transform.toarray()
        expected_transform = expected_transform.astype(np.float32)
        reference_runtime = runtime
    b = np.concatenate([portable.predict_proba(frame.iloc[i:i+256])[:, 1]
                        for i in range(0, len(frame), 256)])
    stress_b = portable.predict_proba(stress)[:, 1]
    transformed = portable.transform(frame.iloc[:256])
    assert np.array_equal(expected_transform, transformed)
    threshold = portable.manifest['threshold']
    worst = float(np.max(np.abs(a-b)))
    stress_diff = float(np.max(np.abs(stress_a-stress_b)))
    disagreements = int(np.sum((a >= threshold) != (b >= threshold)))
    stress_disagreements = int(np.sum((stress_a >= threshold) != (stress_b >= threshold)))
    assert np.isfinite(stress_b).all() and ((stress_b >= 0) & (stress_b <= 1)).all()
    assert worst < 1e-12 and stress_diff < 1e-12
    assert disagreements == stress_disagreements == 0
    result = {
        'source_rows': len(frame), 'source_max_abs_probability_difference': worst,
        'source_threshold_disagreements': disagreements, 'stress_rows': len(stress),
        'stress_max_abs_probability_difference': stress_diff,
        'stress_threshold_disagreements': stress_disagreements,
        'transformed_float32_matrix_exact': True, 'retrained': False,
        'source_reported_sklearn': portable.manifest['source_reported_sklearn'],
        'source_artifact_sha256': digest(source_path), 'reference_runtime': reference_runtime,
        'comparison_runtime': runtime, 'recorded_version_reference': matched,
        'original_representation_ok': repr_ok, 'version_warnings': version_warnings,
        'comparison_mode': 'saved-1.9.1-reference' if portable_only_reference else 'original-object',
        'input_data_sha256': data_sha, 'manifest_sha256': digest(path),
        'scope': 'Numerical equivalence on listed inputs, not prospective accuracy or a recreation of every training-environment dependency.' if matched else 'Incompatible-version diagnostic only. Use the recorded-version reference environment for verification.'
    }
    if reference_output:
        assert matched and repr_ok, 'Reference output requires the recorded sklearn runtime'
        output = Path(reference_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(output, source_probability=a, stress_probability=stress_a,
                            transformed_first256=expected_transform)
        result['reference_arrays_sha256'] = digest(output)
        output.with_suffix('.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--reference-output', type=Path)
    group.add_argument('--portable-only-reference', type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.reference_output, args.portable_only_reference), indent=2))
