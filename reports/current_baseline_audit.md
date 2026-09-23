# Current Prototype Baseline

The existing model and dataset are retained for comparison only. They are not the final research result.

## Existing data

- 2,290 workflow-run rows
- 633 unique repository/commit pairs
- 319 failures (13.93%)
- 4 repositories
- 1,657 repeated repository/commit keys
- 125 commits with both success and failure labels
- 371 unique model feature vectors

## Existing reported model

The current XGBoost report contains ROC-AUC 0.7761, PR-AUC 0.3483, precision 0.3365, recall 0.5469, and F1 0.4167 on a random row split.

## Validity limitation

Of 458 test rows, 395 share their repository/commit key with training. This 86.2% overlap violates the new research protocol. Model selection also used the same test set later reported as final evaluation.

Exploratory chronological and leave-one-repository-out evaluations showed materially weaker generalization. These exploratory values are diagnostic and must be reproduced by the new evaluation pipeline before citation.

The saved pickle remains a prototype artifact for UI compatibility and must not be promoted as the final research model.
