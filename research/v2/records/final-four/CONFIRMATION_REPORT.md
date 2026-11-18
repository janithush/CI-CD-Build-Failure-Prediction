# Untouched frozen-model confirmation

18 November 2026. Models, preprocessing, calibration and thresholds were frozen before new target access. A documented roster amendment followed availability screening, before scoring. New-cohort predictions were scored once.

| Project              |   Rows |   Failures |    B0 AP |    C1 AP |   Difference |
|:---------------------|-------:|-----------:|---------:|---------:|-------------:|
| celery/celery        |    496 |         65 | 0.175758 | 0.175715 | -4.24611e-05 |
| pypa/pip             |    500 |         99 | 0.199301 | 0.197785 | -0.00151612  |
| python-poetry/poetry |    500 |         78 | 0.269309 | 0.269911 |  0.000601291 |
| scrapy/scrapy        |    500 |        161 | 0.481051 | 0.459903 | -0.0211478   |

Equal-project AP: B0 0.28135, C1 0.27583; difference -0.00553. Exploratory project-and-commit interval [-0.02722, +0.01700]. Every leave-one-project-out mean difference is negative. This does not demonstrate C1 improvement, and does not erase the original five-project negative result. Four purposive Python projects cannot establish universal transfer.

Original screening: Scrapy and Celery had 500 selected attempts each, Ansible zero, Textual 16. Requests was excluded because it appeared in old prototype data. Pre-score fixed reserves: pip and poetry each 500; httpx four, below the 200-row eligibility minimum. No further replacements. Celery lost four rows to feature eligibility; frozen-membership.csv retains every exclusion. The primary score includes 1,996 rows from four sufficiently populated projects. All retrieved API records, date-partition membership, commit-file pagination, feature inputs and hashes are retained.

API records expose latest visible attempts, not every historical rerun. Features describe recorded head changes, not full runtime-source attestation. No target outcomes enter features, including change context; outcome-flip and chronological-prefix tests passed before scoring. No target labels fit models, calibration or thresholds.

## Source-threshold probability and warning diagnostics

| model    |    Brier |   log_loss |   ECE_10_equal_width |   warning_rate |    recall |   precision |   false_alarms_per_100_runs |
|:---------|---------:|-----------:|---------------------:|---------------:|----------:|------------:|----------------------------:|
| B0       | 0.163624 |   0.515369 |            0.0965836 |       0.046    | 0.0801282 |    0.271739 |                      3.35   |
| C1       | 0.168352 |   0.528    |            0.118871  |       0.207032 | 0.281623  |    0.25923  |                     15.0024 |
| constant | 0.161541 |   0.504437 |            0.0582379 |       0        | 0         |  nan        |                      0      |

Brier is overall probability error, not pure calibration. Ten equal-width reliability-bin counts are saved. Source thresholds were not tuned to this cohort; offline false alarms do not establish developer utility or safe skipping.
