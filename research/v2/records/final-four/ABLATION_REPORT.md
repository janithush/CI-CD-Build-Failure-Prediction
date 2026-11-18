# C1 feature-group ablations

18 November 2026. All forty fixed fits completed and predictions/holdout separation verified. Source development data only; no old or new external score selected these configurations. Each source fit selects from the original six learned settings and uses separate strict calibration/threshold stages. These are diagnostic refitted-pipeline ablations, not a causal isolated feature effect. Held-project earlier-change context is reset at the April 1 boundary.

| configuration        |   macro_AP |   macro_delta_vs_B0 |   projects_positive_vs_B0 |
|:---------------------|-----------:|--------------------:|--------------------------:|
| B0-plus-logs         |   0.492329 |          0.00843097 |                         3 |
| B0                   |   0.483898 |          0          |                         0 |
| B0-plus-ratios       |   0.480756 |         -0.00314257 |                         3 |
| C1-minus-proportions |   0.472988 |         -0.0109107  |                         3 |
| C1-minus-logs        |   0.47055  |         -0.0133487  |                         2 |
| C1                   |   0.467798 |         -0.0161003  |                         2 |
| C1-minus-ratios      |   0.466624 |         -0.0172741  |                         2 |
| B0-plus-proportions  |   0.457088 |         -0.0268107  |                         1 |

## Per-development-project AP

| held_project      |       B0 |   B0-plus-logs |   B0-plus-proportions |   B0-plus-ratios |       C1 |   C1-minus-logs |   C1-minus-proportions |   C1-minus-ratios |
|:------------------|---------:|---------------:|----------------------:|-----------------:|---------:|----------------:|-----------------------:|------------------:|
| Kludex/starlette  | 0.37049  |       0.349818 |              0.319355 |         0.3028   | 0.299893 |        0.287153 |               0.310776 |          0.335141 |
| fastapi/fastapi   | 0.459257 |       0.458581 |              0.455839 |         0.479068 | 0.48416  |        0.490464 |               0.481754 |          0.470255 |
| pallets/flask     | 0.88407  |       0.885802 |              0.886636 |         0.935431 | 0.929744 |        0.946812 |               0.948604 |          0.8861   |
| pytest-dev/pytest | 0.160461 |       0.174386 |              0.135212 |         0.134664 | 0.156558 |        0.14648  |               0.168509 |          0.151323 |
| tiangolo/typer    | 0.545213 |       0.593059 |              0.488397 |         0.551815 | 0.468636 |        0.481839 |               0.455294 |          0.490301 |

The configurations and five folds were fixed before fitting. All results are shown, including worse settings. No ablation winner replaces the locked B0/C1 confirmation models. Five source folds share training data and are not five independent confirmations. The original external C1 negative result remains unchanged.
