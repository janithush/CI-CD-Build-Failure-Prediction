# Combined dashboard contract and baseline

Status: implementation plan for review, not a merged release. Base: ae420f5. The current v1.0.0/v2.0.0 tags and all scientific results must remain unchanged.

## Baseline actually exercised

The original API was started locally. The public thesis repository was connected through GitHub without a token; its actual ae420f5 commit was passed to prediction and appeared in local history. The captured connection fixture contains public repository/commit metadata, not invented commits. Previous-error text is excluded. The live model returned a score, but scikit-learn reported an artifact/runtime version mismatch: original live artifact 1.9.1, research runtime 1.7.2. A returned number under these warnings is not supported-runtime validation.

## UI inventory

Preserve repository chips and URL input, optional token reveal control, Connect repository, Predict, Change repository, Copy SHA, feedback submit, history pagination and refresh. Add Research evidence inside the existing visual shell, not an unrelated replacement. The existing v2 has only two dropdowns and an attribution link. It does not provide live inference.

## Response contract

- `ml_failure_probability`: untouched model probability in percent for legacy compatibility. Never modified by advice rules.
- `raw_model_probability`: explicit alias in percent.
- `advisory_risk_score`: separately labelled rule-adjusted advisory score, not a probability.
- `final_failure_risk_score`: compatibility alias for the advisory score.
- `model_info`: actual artifact identity/hash, threshold, runtime and model label; no fabricated metric fallback.
- `provenance`: repository, commit, workflow/attempt identity, prediction cutoff, feature-contract version, route, input completeness and missingness.
- Historical research panels must say frozen study evidence. Their metrics do not measure the newly connected repository.

## Service boundaries

A legacy live path remains distinct from the strict research model service. The research runtime is pinned to the original 1.7.2 environment. Do not load the legacy 1.9.1 artifact inside that runtime without validation; an isolated matching worker is an acceptable boundary. No current/future outcome or current log enters strict prediction features. If strict inputs cannot be verified, return unavailable, not an invented history or a silent legacy fallback.

## History, feedback and security

Persist raw score and advice separately with identity/provenance. Feedback is recorded evidence, not retraining. Remain a loopback-only local demo until separate access/security/deployment review. Never persist a GitHub token in browser storage, logs or records. No new workflow execution, model training, thesis changes or deployment is authorized by this contract.

## Baseline tests and acceptance

The protected-file hash fixture records the frozen research data/models/results. Unit checks must keep those bytes unchanged. Later stages must exercise normal live connection/prediction/history plus controlled error tests, strict-model replay parity and keyboard/mobile interaction. A fixture test must be labelled a fixture test, not a fresh provider or scientific result. Maintain one issue/branch/PR per stage, include Closes references, and await Janith's merge approval.
