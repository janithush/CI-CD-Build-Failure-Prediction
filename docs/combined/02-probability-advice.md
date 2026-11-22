# Raw probability and advisory score

The raw model output is preserved at full returned precision in `raw_model_probability` and `ml_failure_probability` (percent). Advisory rules produce `advisory_risk_score`; `final_failure_risk_score` remains its compatibility alias. `advice_adjusted` states whether rules moved the rounded score. Advice is not a calibrated probability.

The UI shows the raw percentage separately from the advisory score out of 100. Reasons state the raw model's actual relationship to its threshold, even when advisory rules recommend a higher risk class. Historical metrics are not new v2 validation. Existing header/architecture panels and feedback wording remain part of the upcoming integrated-UI work, not endorsed by this change.

Checks: two probability tests pass, including the captured real public commit and an explicitly controlled low-model/high-rule unit case. Three baseline contract tests pass; scientific hashes unchanged. The browser Connect/Predict flow was rerun on the actual public commit and inspected. The inherited model dependency mismatch remains unresolved and is not validated by these functional checks. No frozen model, data, result, tag or release changed.
