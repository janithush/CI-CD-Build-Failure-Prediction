# Security and trusted local research

Upstream history contains a token-shaped literal removed from the current source. Janith reports that the upstream owner removed that token in GitHub token settings, revoking it. This report was not independently verified by using the token. Never use credentials found in source history. No credential value is reproduced in this note.

Current research additions were scanned for common credential patterns, including decompressed research tables. A scan is not proof of absence. Raw provider caches, CI log ZIPs, private thesis files, personal notes and local authentication files are excluded from the additions.

The retained prototype is for local research, not an authenticated production service. The inherited GitHub Actions workflow is stored as an inert `.disabled` template. Review it before enabling any automation. Fitted pickle/joblib models can execute code when loaded: only load trusted files after checking the supplied integrity manifest.

## Combined candidate: not approved for hosting

Bind both servers to 127.0.0.1. API requests from remote clients and non-local HTTP origins are refused; CORS is restricted and credentials are not allowed through it. This is a local single-user boundary, not authentication or tenant isolation. Do not expose a tunnel/reverse proxy or override these checks to host the demo. Broader deployment needs separate authorization, authentication, user/repository authorization, retention review and security acceptance.

Only explicit public-read server credentials or a legacy session token are used. Repository .env fallback is disabled. No token is placed in browser storage, records or responses. Research records use a fixed field whitelist; free-text logs and credentials are not accepted as assessments. Frozen replay/preview does not collect target outcomes or trigger a workflow.

Legacy feedback without prediction identity is refused, rather than associating a prior run's outcome with another commit. Research feedback is only a fixed-choice usefulness assessment of the exact displayed record; no automatic learning or verified retraining occurs. Existing local legacy history is not rewritten or deleted.
