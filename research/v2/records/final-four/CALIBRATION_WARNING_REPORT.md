# Calibration and warning analysis

18 November 2026. Existing five-project external cohort only; new-cohort addition is still pending. All thresholds and calibration are source-only. No target threshold tuning or recalibration. Ten fixed equal-width reliability bins include counts, with no claim of stable calibration from sparse bins. ECE depends on binning. Constant uses source-fit prevalence 0.17969744097271315. Its warning counts use the fixed B0 policy for comparison, not its own target-optimized threshold.

|                            |    Brier |   log_loss |   ECE_10_equal_width |   warning_rate |    recall |   precision |   false_alarms_per_100_runs |
|:---------------------------|---------:|-----------:|---------------------:|---------------:|----------:|------------:|----------------------------:|
| ('online', 'B0')           | 0.147958 |   0.471211 |            0.0825777 |         0.1368 | 0.274886  |   0.374566  |                        8.2  |
| ('online', 'C1')           | 0.147446 |   0.469114 |            0.0774891 |         0.1464 | 0.268976  |   0.336688  |                        9.4  |
| ('online', 'constant')     | 0.155287 |   0.489615 |            0.0552605 |         0      | 0         | nan         |                        0    |
| ('zero-label', 'B0')       | 0.160219 |   0.501686 |            0.0918098 |         0.0552 | 0.0825397 |   0.0948905 |                        4.48 |
| ('zero-label', 'C1')       | 0.16525  |   0.521329 |            0.112735  |         0.1768 | 0.260818  |   0.320906  |                       13.48 |
| ('zero-label', 'constant') | 0.155287 |   0.489615 |            0.0552605 |         0      | 0         | nan         |                        0    |

These are equal-project descriptive means. Per-project counts and confusion matrices are in calibration-warning-by-project.csv. Precision is undefined when no warnings occur and is left blank, not set to a favourable value. The figures do not show time savings, utility, safe skipping or prospective validation. Source alert thresholds may transfer poorly; model ranking and calibration are different questions. Original negative C1 transfer findings remain unchanged.
