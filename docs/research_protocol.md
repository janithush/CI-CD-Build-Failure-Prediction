# Research Protocol

## Research question

Can information available immediately before a GitHub Actions workflow run starts predict whether that workflow run will fail?

## Unit of analysis

One observation is one workflow-run attempt. Its stable key is:

`repository + run_id + run_attempt`

A commit may trigger several workflows. Those runs are different observations because their workflow definitions and historical behavior differ. Attempts of a rerun are retained separately.

## Prediction time

The prediction cutoff is immediately before `run_started_at`. Every model feature must have an event timestamp strictly earlier than that cutoff or be static information available at that cutoff.

The following are prohibited as inputs for the run being predicted:

- its conclusion, duration, jobs, steps, logs, or failed step;
- later attempts or later workflow runs;
- statistics calculated with the current or future outcome;
- post-build feedback for the current run.

## Outcome

- `build_result = 0`: completed workflow-run attempt concluded `success`.
- `build_result = 1`: completed workflow-run attempt concluded `failure`.

The primary experiment excludes `cancelled`, `skipped`, `neutral`, `timed_out`, `action_required`, `stale`, and incomplete runs. These outcomes are preserved in raw storage for later sensitivity analyses.

## Population and sampling

The target population is active public software repositories using GitHub Actions. The final sample should include 50-100 non-fork repositories, 50,000-100,000 completed workflow runs, at least 5,000 failures, at least 500 workflows, 6-10 programming languages, and 12-24 months of history.

Repositories must have at least 200 completed runs, at least 20 failures, traceable commit-run relationships, and meaningful build/test workflows. Issue-management-only, stale-bot, labeling-only, and equivalent administrative workflows are excluded from the primary experiment.

## Evaluation protocol

1. Sort observations chronologically.
2. Use the oldest 70% for training, next 15% for validation, and newest 15% for final testing.
3. Keep repository/commit groups together wherever commit-derived observations could cross a boundary.
4. Fit imputers, encoders, resampling, feature selection, calibration, and thresholds on training/validation data only.
5. Select models on validation data. Evaluate the final test set once.
6. Run leave-one-repository-out evaluation as the external-generalization analysis.
7. Report PR-AUC, recall, precision, F1, MCC, ROC-AUC, Brier score, calibration error, confusion matrices, and 95% bootstrap confidence intervals.

## Required baselines

- majority/no-information classifier;
- global historical failure rate;
- repository historical failure rate;
- workflow historical failure rate;
- previous result for the same workflow;
- logistic regression;
- decision tree;
- random forest;
- gradient boosting/XGBoost.

## Feedback policy

Post-build records are feedback collection, not automatic learning. A new model may be deployed only after label validation, drift checks, leakage-safe retraining, challenger evaluation, and explicit approval. The currently deployed model must remain available for rollback.

## Privacy

Developer identifiers are pseudonymized with a salted hash. Names and email addresses are not included in model-ready datasets or reports. Secrets and GitHub tokens are never written to datasets, logs, browser storage, or source control.

## Current baseline status

The existing 2,290-row model is retained only as a prototype baseline. Its random row split leaks repository/commit identities: 395 of 458 test rows share a commit with training. Its published-style score must not be treated as final research evidence.
