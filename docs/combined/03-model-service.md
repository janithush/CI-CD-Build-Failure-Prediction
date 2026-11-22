# Strict research model service

The new service verifies the immutable research artifact hash and matching scikit-learn 1.7.2 runtime before loading. It supports frozen replay across all original models/regimes and an explicitly prospective cold-onboarding live preview. It does not fit a model or edit scientific artifacts.

## Live preview

A public repository and active workflow are required. The provider reads real repository metadata, the exact current default-branch commit and its complete file metadata (maximum under 300 files), and the workflow definition at that exact SHA. Request time is the explicit prospective push/first-attempt scenario cutoff, not an assertion about an already observed run. All target outcomes and earlier target change context are deliberately withheld at this cold boundary; that matches the supported no-history route. Known four past-mean-relative fields remain missing rather than being invented.

The adapter reuses the archived research file aggregation and change-context definitions and an exact copy of the reviewed static workflow descriptor function. Live online-history mode is not offered: full released terminal-job evidence and pair history are not currently collected by this service. Frozen online replay does preserve the original route gate and thresholds. This is not a claim of live accuracy or predictive superiority.

Only fixed GitHub API hosts are read, with bounded requests, explicit timeouts and no automatic retry on access/rate-limit errors. An optional operator-supplied `BUILDRISK_PUBLIC_READ_TOKEN` remains server-side and is never part of the returned provenance or persisted record. No private repository preview, log retrieval, workflow trigger or write is implemented. Anonymous reads can hit GitHub rate limits. An active-workflow listing can be stale; a missing exact-commit definition returns unavailable, not a fabricated score.

## Real test and parity evidence

Seven service tests pass, including all nine frozen probability vectors at maximum absolute difference below 1e-12, exact case identity, missing-feature rejection, current/future-outcome flip invariance, cold input/timestamp checks, fixed-host validation and no rate-limit retry. Baseline protected scientific hashes remain unchanged.

A real public read of pallets/flask, commit 49943b5a94413a530761350f04e896f76e8d620e, Tests workflow 1367898 produced a C1 no-history preview using the actual commit and exact workflow definition. It was a prospective scenario at the displayed cutoff, not a prediction claimed before the existing commit's original run. Source URLs are retained in the result. No workflow was triggered. Initial anonymous testing also exposed a stale active-workflow definition and GitHub access/rate limiting; both returned unavailable.

## Legacy compatibility limit

The inherited served artifact reports scikit-learn 1.9.1, unavailable from the tested package index. Its unsupported-runtime prediction is now explicitly disabled with a 503 response rather than silently returning an unvalidated score. No version metadata is rewritten and no artifact is retrained. The original UI workflow is retained for later integrated handling; its legacy prediction option must show this availability state. A supported isolated runtime or separately approved migration would be needed to restore that exact artifact safely.

Install `requirements-combined.txt` in a fresh environment for research serving. API routes are `/research/status`, `/research/workflows`, `/research/preview` and `/research/replay`. All remain local research routes, not a production deployment.
