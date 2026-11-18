# Source ledger

- GitHub Actions REST workflow runs: https://docs.github.com/en/rest/actions/workflow-runs . Primary API documentation, fetched November 18. Specific-attempt endpoint semantics and rerun scope.
- GitHub Actions REST workflow jobs: https://docs.github.com/en/rest/actions/workflow-jobs . Primary API documentation, fetched November 18. Jobs are runner-level sets of steps; specific-attempt job listing and timestamps.
- GitHub Actions workflow syntax: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax . Primary documentation, fetched November 18. runs-on labels, expressions and job declarations.
- GitHub matrix documentation: https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations . Primary documentation, fetched November 18. Matrix axes and dynamic expressions; declaration product is not full executed job expansion.
- The Importance of Discerning Flaky from Fault-triggering Test Failures: https://arxiv.org/abs/2302.10594 . Research preprint/academic case study, fetched November 18. Motivates not equating flaky tests with harmless failures; its numerical findings are not transferred to this study.
- Understanding and Detecting Flaky Builds in GitHub Actions: https://arxiv.org/abs/2602.02307 . Research preprint, fetched November 18. Rerun-based build-flakiness analysis as related work; no numerical claim imported.
- Primary empirical evidence: preserved provider response URLs and HTTP statuses in responses/*.json and log-retrieval/*.json; prior fixed cohort and manifests; original source repositories listed in the source/target manifests. These are observed records, not causal guarantees.
