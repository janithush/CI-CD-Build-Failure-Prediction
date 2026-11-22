# Stage 5: loading, failure and recovery

Both the combined study panel and the archived v2 view use a shared strict results schema. Until all regimes, model rows, project rows and finite metric fields validate, selectors remain disabled and result tables stay empty. Missing files, invalid JSON, wrong schemas, duplicates and impossible metrics produce an actionable message without fallback scores. Explicit reload can recover. Direct file opening explains the local HTTP requirement.

Browser fault tests: `python tests/browser_error_states.py`.

The controlled test covers eight failure cases in both views (16 failures and 16 successful retries), a delayed response/loading state and direct-file guidance. No external provider is called. Tests passed; the malformed-data screenshot was inspected. Original frozen JSON/model/result hashes still pass. API reads have bounded timeouts and structured HTTP checks; repository changes invalidate old workflow responses.

No deployment, merge, release or scientific re-evaluation is included.
