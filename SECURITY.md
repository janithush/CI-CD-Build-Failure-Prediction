# Security and trusted local research

Upstream history contains a token-shaped literal removed from the current source. Janith reports that the upstream owner removed that token in GitHub token settings, revoking it. This report was not independently verified by using the token. Never use credentials found in source history. No credential value is reproduced in this note.

Current research additions were scanned for common credential patterns, including decompressed research tables. A scan is not proof of absence. Raw provider caches, CI log ZIPs, private thesis files, personal notes and local authentication files are excluded from the additions.

The retained prototype is for local research, not an authenticated production service. The inherited GitHub Actions workflow is stored as an inert `.disabled` template. Review it before enabling any automation. Fitted pickle/joblib models can execute code when loaded: only load trusted files after checking the supplied integrity manifest.
