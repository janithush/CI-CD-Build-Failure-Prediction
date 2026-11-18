# Non-code signals: bounded extension and before/after results

18 November 2026. This extension implements the feasible measurement and prediction checks, but it does not turn observational CI records into verified causal code/non-code labels.

## Answer

The added run-time/OS/matrix declaration features produce small cold-history AP changes, not a demonstrated reliable gain. The richer online-history extension is worse. False alarms increase substantially at the fixed source-selected thresholds. Original C1 results remain unchanged; no model was deployed or tuned against the external scores.

## 1. Archive gate and repaired source omission

Before new experiments, all 123 files created in the thesis archive from November 17 through the morning gate were listed and downloaded again (1,253,324,533 bytes). Sizes, hashes, 34 archive structures and available part manifests checked out. The latest saved Word/PDF/log matched their local final bytes.

That file-integrity gate was necessary but did not establish reference closure. During the deeper source check, the previous 500-case log manifest referenced 496 available raw ZIPs, while only 362 were in its archived raw-log checkpoint. All 134 omitted ZIPs were retrieved from the provider, and all 134 match their previous recorded SHA-256 hashes exactly. The repaired supplement is included with this extension. All 496 raw ZIP hashes were then checked against the frozen manifest. Four genuine provider-404 cases remain absent. The original claim is narrowed: stored files were intact, but completeness of referenced raw sources required this later repair. New model predictions were already fixed when the omission was found and were not changed.

## 2. Rerun evidence

All observed run IDs with run_attempt greater than one were screened in the existing development and two external cohorts. The collector requested 421 earlier-attempt records: 418 returned 200 and three returned 404. Combined with the fixed latest observed rows, this yields 471 within-run attempt pairs. Pairs must share the recorded workflow and head SHA. A repeated run may contribute more than one pair, so pair counts are not independent runs.

| cohort         |   pairs |   runs |   failure_then_success_pairs |   runs_with_failure_then_success |
|:---------------|--------:|-------:|-----------------------------:|---------------------------------:|
| later4-zero    |     191 |    158 |                           66 |                               58 |
| original5-zero |     131 |     93 |                           46 |                               37 |
| source         |     149 |    131 |                           40 |                               36 |

There are 152 failure-to-success pairs across 131 distinct run IDs (36 development, 37 original-external and 58 later-external). These are outcome-discordant reruns, not confirmed non-code or flaky root causes. Unpinned dependencies, selected failed-job reruns, caches, external services, event state, test ordering and unobserved executed source can differ despite the same recorded head. Conversely, no discordance does not establish determinism. Nothing was actually rerun by this study. Selection starts from API-visible latest attempts and cannot estimate population flakiness prevalence. Same-head separate-run evidence is weaker and is used only as a historical feature, not merged into the within-run rerun counts.

## 3. Failure-log signatures and scope

The previous frozen evidence cohort is unchanged: 500 attempts, 413 provider successes and 87 failures. All 496 available raw ZIPs now match their earlier hashes. The prior 100 MiB expanded top-level job-log bound remains; one oversized attempt stays unknown. Failed-step intervals were joined to exact job names, using inclusive provider timestamps with one-second uncertainty. Of 378 failed-step records, 368 have uniquely matched log evidence. Missing or ambiguous matches do not become negative evidence.

Fixed patterns mark assertion/test summaries, compile/build messages, resolution/transport errors, active timeout errors and dependency/environment messages. These are overlapping symptom signatures, not causal ground truth. An ImportError can reflect a code/configuration change; a timeout can be a performance regression; an assertion can fail because of environment state. Network and timeout labels were checked for false substring/configuration hits and narrowed to avoid treating ModuleNotFoundError as ENOTFOUND or pytest-timeout installation/configuration and documentation spelling output as an actual timeout. All five final environment-like cases were manually checked against their exact failure-step evidence. Conservative exclusion of documentation/spelling timeout words can miss real failures and does not prove the other cases harmless. The initial audit used an incomplete earlier job cache; it was replaced by the already-archived complete 2,500-run cache. Draft audit tables are retained. These are parser/data-recovery corrections, not performance-guided feature or threshold selection. The original primary labels and predictions do not change.

Failure strata after those checks:

| scope_category             |   failures |
|:---------------------------|-----------:|
| environment_like_supported |          5 |
| mixed_observed_signatures  |          3 |
| test_or_compile_supported  |         39 |
| unknown                    |         40 |

The 40 unknowns include four unavailable raw logs, one oversized log and 35 parsed attempts without the specified failed-step signatures. A missing signature is not evidence of no code defect. The mixed group stays separate. No forced binary causal relabelling or unsupported code-only model is produced.

## 4. Prediction-time extension

B0 already includes workflow/repository/branch failure history and commit-clock features; this work does not claim those were absent. The extension adds 17 static numeric descriptors: cyclic run-start hour/week, observed attempt index, definition availability, declared job count, matrix-axis count and product, include/exclude entry counts, reusable-job count, dynamic-expression marker and declared Linux/Windows/macOS/self-hosted indicators. Matrix-axis products ignore include/exclude semantics and are declarations, not executed job counts. Dynamic products remain unknown; expressions and reusable workflows are not executed or fully resolved. Every feature row has a retrieved root definition, but root availability is not complete runtime-source attestation.

The history branch adds six released-evidence descriptors: workflow consecutive-failure streak, earlier same-head count/failure fraction, and observed workflow rerun-pair count/discordance count/fraction. One first observed binary pair per run is released for this history, avoiding combinatorial pair weighting. Release must be strictly before prediction start. Current logs, current job outcomes, later reruns and current test-failure identities are not prediction inputs. Source updated_at remains the earlier disclosed availability proxy; original-external online outcomes additionally require complete terminal-job evidence.

A consistent per-test identity/execution ledger does not exist in these source records. Test-level failure history is therefore not fabricated; workflow-level history is the implemented granularity. This is an explicit coverage limit of option 3.

The original six learned settings are tried on source data only. Whole-commit maturity-aware fit/selection/calibration/threshold stages before July 1, 2026 have 7,073/1,273/1,159/1,222 rows. The selected static branch is random forest depth 10; the history branch is XGBoost depth 5. Sigmoid calibration and warning thresholds use source-only stages. Source models and input/code hashes were locked before their new target predictions. The online policy retains the existing route: history branch after at least five released workflow outcomes, otherwise the static no-history branch. Model-selection differences mean this is a whole refitted-pipeline comparison, not an isolated causal effect of one feature.

## 5. Matched before/after results

Original five-project rows: 2,500. Later four-project rows: 1,996. Baseline predictions were regenerated from the preserved original models and match to floating precision. All models use identical rows in each reported comparison. All external projects had already been viewed; the extension is exploratory evaluation, not another untouched confirmation. No feature/threshold choice was made from these scores.

| regime           | model    |       AP |    Brier |   warning_rate |   false_alarms_per_100_runs |
|:-----------------|:---------|---------:|---------:|---------------:|----------------------------:|
| later4-zero      | B0       | 0.281355 | 0.163624 |       0.046000 |                    3.350000 |
| later4-zero      | C1       | 0.275829 | 0.168352 |       0.207032 |                   15.002419 |
| later4-zero      | extended | 0.284927 | 0.164161 |       0.344964 |                   25.738710 |
| original5-online | B0       | 0.354504 | 0.147958 |       0.136800 |                    8.200000 |
| original5-online | C1       | 0.352472 | 0.147446 |       0.146400 |                    9.400000 |
| original5-online | extended | 0.311159 | 0.155448 |       0.211600 |                   15.040000 |
| original5-zero   | B0       | 0.286259 | 0.160219 |       0.055200 |                    4.480000 |
| original5-zero   | C1       | 0.279388 | 0.165250 |       0.176800 |                   13.480000 |
| original5-zero   | extended | 0.288342 | 0.158995 |       0.407600 |                   30.960000 |

Extended minus C1 AP: original-five cold +0.00895, later-four cold +0.00910, original-five online -0.04131. Against B0 the cold differences are only +0.00208 and +0.00357; online is -0.04335. Exploratory paired project/commit 95% intervals for extended minus C1 (500 draws, seed 42) are:

- later4-zero: [-0.02547, +0.04142]
- original5-online: [-0.06578, -0.01021]
- original5-zero: [-0.00845, +0.02502]

Purposive projects, shared ecosystems and previously viewed targets limit these intervals. Cold intervals include zero; there is no reliable demonstrated transfer gain. The online extension deteriorates. At source-selected thresholds, original-five cold false alarms rise from C1 13.48 to 30.96 per 100 runs, and later-four from 15.00 to 25.74. Better cold AP does not establish better operational utility. Brier is overall probability error, not pure calibration; reliability-bin counts and warning confusion totals are saved separately.

## 6. Evidence-stratified descriptive results

Each retrospective failure stratum is compared with all 413 provider successes. These are pooled AP values, not equal-project means and not directly comparable with the primary cohort AP. Failure groups are small and outcome-selected, and test execution is not verified for every success. The rows are not a representative sample of causal code/non-code failures.

| stratum                    | model    |   rows |   positives |   pooled_AP |
|:---------------------------|:---------|-------:|------------:|------------:|
| test_or_compile_supported  | B0       |    452 |          39 |    0.090596 |
| test_or_compile_supported  | C1       |    452 |          39 |    0.103821 |
| test_or_compile_supported  | extended |    452 |          39 |    0.182400 |
| environment_like_supported | B0       |    418 |           5 |    0.028443 |
| environment_like_supported | C1       |    418 |           5 |    0.023860 |
| environment_like_supported | extended |    418 |           5 |    0.039072 |
| mixed_observed_signatures  | B0       |    416 |           3 |    0.011659 |
| mixed_observed_signatures  | C1       |    416 |           3 |    0.010639 |
| mixed_observed_signatures  | extended |    416 |           3 |    0.007315 |
| unknown                    | B0       |    453 |          40 |    0.080586 |
| unknown                    | C1       |    453 |          40 |    0.091857 |
| unknown                    | extended |    453 |          40 |    0.133619 |

These tables answer what happens under explicit evidence strata, not whether a failure was caused by the commit. No validated code-caused endpoint or non-code detector has been established. A causal code-only prediction claim would require source cause labels and independent validation that these data do not supply.

## 7. Checks and limits

Independent checks reproduced every AP/Brier score from saved predictions, checked confusion totals and regenerated original baseline predictions. Added histories passed chronological-prefix, current/future-outcome flip and future-pair-removal invariance in development and online evaluation. No dummy observations or synthetic results enter the analysis. All tested settings, negative results, code, response URLs/statuses, models, predictions, audit pointers, parser corrections and repaired raw sources are preserved.

No push, workflow trigger, production deployment, automatic skipping or user-cost claim was made. The four requested areas have been investigated with real evidence, while genuine per-test history and causal code/non-code truth remain unavailable rather than falsely marked solved.
