# Stage 7 acceptance report

Candidate: stacked stage-7 branch. Tests cover implementation behavior, not new scientific validation. No CI workflow, training, release, merge or deployment is activated.

## Results

- 31 unit tests pass, including unchanged frozen hashes, all nine probability-vector replays within 1e-12, strict cold boundaries, outcome exclusion, unsupported legacy runtime, repository isolation, credential whitelist, explicit-token behavior, feedback identity and local-only origin/client restrictions.
- Public-provider failures 401/403/404/429/500 and timeout refuse a score without automatic retry. Missing/private/stale metadata is refused. Legacy reads now have explicit 20-second request bounds.
- Browser acceptance exercises the original controls with a captured real-connection fixture and clearly controlled advice/history responses, including low raw probability versus high advice, clipboard, token visibility, disabled unbound feedback, pagination and refresh.
- Nine actual local fitted-model replays cover every regime/model choice. Record export, three usefulness assessments, repository history and refresh isolation pass.
- Workflow discovery rate-limit and preview rendering are tested with explicit controlled responses. This is not passed off as real provider evidence.
- A separate explicit read-only public run discovered Flask's Tests workflow and produced a real C1 cold scenario preview at exact commit 49943b5a94413a530761350f04e896f76e8d620e. Raw probability 0.3023001535421241; threshold 0.385. The exported record includes artifact/input hashes, request-time cutoff, workflow identity, missingness and API sources. No CI was triggered.
- Zero browser JavaScript errors in acceptance. Keyboard focus, navigation to and from the archived viewer, refresh, 1440px desktop, 390px portrait and 844px landscape pass. Screenshots inspected directly, including probability/provenance and narrow-screen wrapping. No whole-page horizontal overflow.
- 16 controlled missing/malformed-data failures and 16 successful retries pass in both study views, plus delayed loading and direct-file guidance.

## Repeat locally

Install the combined requirements and test dependencies from the final setup notes, then:

```bash
python -m unittest discover -s tests -p 'test_*' -v
python tests/browser_error_states.py --screenshots evidence/errors
python tests/browser_combined.py --screenshots evidence/local
```

The last command is external-call-free by default. For an explicitly authorized public metadata read only:

```bash
python tests/browser_combined.py --screenshots evidence/public --live-public-repository pallets/flask --workflow-id 1367898
```

An optional server-side `BUILDRISK_PUBLIC_READ_TOKEN` must be supplied securely, never saved in source or shell history. The script uses a disposable operational database and stops its local servers. It does not enable CI.

## Remaining limits and acceptance decision

Not production-ready. The inherited artifact is incompatible with this runtime and its prediction is disabled. Online released-history serving is available as frozen replay only. Live preview is a first-attempt cold scenario, not an already recorded run forecast. Usefulness assessments are not verified outcomes or training. The app is single-user, local-only; authentication and multi-user deployment require a separate design/review. Third-party provider state and package availability can change.

No accuracy gain, safe CI skipping, causal diagnosis or measured developer benefit is established. Scientific findings, thesis files, existing release tags and master are unchanged. Merge/release still require Janith's approval.
