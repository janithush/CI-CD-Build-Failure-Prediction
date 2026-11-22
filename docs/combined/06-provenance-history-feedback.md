# Stage 6: provenance, local history and feedback boundaries

Every research preview/replay now stores an immutable local record: repository, exact commit, workflow, real run/attempt when replayed, hypothetical first attempt when previewed, cutoff, selected model/artifact hash, feature contract, route, raw fractional probability, source-selected threshold, missingness, input features and canonical input hash. Advisory score is explicitly null because research inference does not add legacy heuristic advice. Scientific artifacts/results are not changed.

The exact record can be exported and re-opened from repository-scoped history. Required repository scope prevents an empty filter from returning other projects. Records are single-user local data, not multi-user account isolation.

## Feedback

The old endpoint had no prediction identity and could attach a previous run's result to a new commit. It is disabled, returning HTTP 409. Its visual shell remains, clearly unavailable. There is no unsupported claim that a scenario has a verified CI outcome.

The new assessment accepts only prediction ID, matching repository and a fixed usefulness choice. It stores an annotation bound to that record. No free-text logs/credentials or claimed actual outcomes are accepted. It never modifies prediction records, training data, models or frozen evidence. A genuine pre-execution run-bound prediction/outcome workflow is future work, not silently simulated here.

## Local security boundary

- Loopback clients and local HTTP dashboard origins only. Remote clients/origins are refused. CORS is no longer a wildcard.
- No authentication or multi-user hosting clearance is claimed. Bind API and static server to 127.0.0.1. Do not expose through a proxy, tunnel or public deployment.
- Local records use an explicit field whitelist, excluding request tokens and raw logs. Browser persistence remembers repository identifiers only, not tokens, commit evidence or prediction snapshots.
- Legacy connection uses an explicitly entered session token only; it no longer silently loads a repository .env token. Research public reads use only the explicit server-side public-read environment setting.
- Existing local legacy records are not deleted or rewritten. New research tables are separate. There is no retraining, CI triggering, deployment, merge or release.

## Checks

Five storage/security tests pass: exact record/history equality, repository isolation, feedback identity and unchanged record, dropped credential/log fields, forbidden origins/remote clients and bounded frozen-case identities. All 24 current unit tests pass.

An actual local fitted-model replay was exercised in a browser through record creation, usefulness assessment, repository history, exact JSON export and refresh. Token persistence checks passed. Screenshot inspected. These are implementation tests, not new scientific validation.
