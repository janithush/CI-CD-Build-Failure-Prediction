# CI/CD Build Failure Prediction: research version 2

Research extension by Janith Gunathunga. Original project by [mhdshukry (Shukri)](https://github.com/mhdshukry/CI-CD-Build-Failure-Prediction), based on upstream revision `6cd82763bafc1657501c2df8df39996b273e7e63`.

## Status and ownership

This is Janith Gunathunga's native public fork of Shukri's project. Version 1 is Shukri's original project; version 2 is Janith's research extension. Janith reports that Shukri gave him verbal permission to use and modify the project. This records Janith's account of that permission, not an open-source licence for inherited code or an ownership transfer.

Upstream has no licence file in the inspected revision. Inherited code and upstream-derived helpers retain their original rights. The MIT grant in `LICENSE-MIT-JANITH.txt` applies only to the independently authored additions explicitly listed in `LICENSING.md`, not the whole repository, inherited code, datasets or fitted models.

Native GitHub fork history includes a removed token-shaped literal in an old upstream commit. Janith reports that Shukri removed the token from GitHub's token settings, revoking it. Revocation has not been independently tested. The old value has never been used for this work. No new credential is included in the research additions. See `SECURITY.md`.

## Version 1 versus version 2

| | Version 1: upstream prototype | Version 2: research record |
|---|---|---|
| Author / attribution | Shukri and the original project contributors | Janith's research extension, retaining all upstream credit |
| Interface | Original repository analysis and live score UI | Frozen matched evaluation and evidence dashboard |
| Models | Original served model, fallback features and display overlay | Repaired original benchmark, B0/C1 branches, exploratory extended branches |
| What the score means | Prototype served output, not validation of the repaired models | Historical model probabilities on frozen features, not a live production score |
| Evaluation | Earlier stored reports remain historical | Strict recorded-availability history, commit-separated mature source stages, external comparisons, ablations, audit and warning diagnostics |
| Finding | Do not reuse old headline metrics as new research proof | No demonstrated C1 transfer gain; uncertain cold extension changes, worse online AP and more false alarms |
| Feedback | Existing live feedback mechanism retained | No automatic learning, deployment, build skipping or threshold tuning |

Version numbering here names the two research views. It is not a claim that upstream's own API version numbers were 1 and 2. Version 1 is the inspected upstream snapshot, not an invented earlier commit. `README_V1.md` preserves its original README verbatim; its historical paths and claims have not been endorsed as the current research findings.

## Open the dashboard

For the results-only dashboard, no backend or account is needed:

```bash
python -m http.server 8080
```

Open `http://127.0.0.1:8080/dashboard/research-v2.html`. The **Research version** selector is in the right panel on both screens. Version 1 opens the original prototype. Version 2 opens the evaluated research record. The mobile layout puts the selector above the content.

To use the original prototype's live functionality, install the original requirements and run its API separately:

```bash
pip install -r requirements.txt
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Keep the dashboard at port 8080. Its v1 API requests use localhost port 8000. This setup is for local research, not a hardened public deployment. Do not expose it on the internet without reviewing authentication, CORS, retention and tenant isolation. Tokens must come from environment variables or the explicit local input, never a committed file or browser persistence.

## Reproduce the new research

See [`research/v2/README.md`](research/v2/README.md). The bundle includes frozen features and predictions, source-stage manifests, fitted research models, portable verification/replay/refit commands, and the executed scientific scripts as archival records. It does not include raw CI logs, private dissertation files, private notes, credential material in this research bundle. The native fork separately retains upstream git history, including the security caveat above.

### Main results: equal-project average precision

| Regime | B0 | C1 | Extended |
|---|---:|---:|---:|
| Original 5, cold history (2,500 rows) | 0.28626 | 0.27939 | 0.28834 |
| Later 4, cold history (1,996 rows) | 0.28135 | 0.27583 | 0.28493 |
| Original 5, online history (2,500 rows) | 0.35450 | 0.35247 | 0.31116 |

AP is not accuracy. The extended-minus-C1 cold intervals include zero. All nine external projects were already viewed before the extension, so it is exploratory. In the original-five cold cohort, false alarms rise from C1 13.48 to extended 30.96 per 100 runs at the fixed source thresholds. Better cold AP is not evidence of operational benefit.

Observed same-recorded-head reruns and environment-like log signatures do not establish causal non-code failures. The fixed failure audit has 39 test/compile-like, five environment-like, three mixed and 40 unknown failures. Consistent per-test history is unavailable. No result is manufactured to fill that gap.

## Attribution and retained evidence

`UPSTREAM_PROVENANCE.json` records the exact upstream revision and snapshot hashes. Original rights remain with the respective authors. The complete private research archive remains the source for raw provider records and original execution layout. Frozen research pickles are included only for trusted local replay: never load an untrusted pickle/joblib file. Dependency versions are recorded for reproducibility, not a promise of indefinite compatibility.

No GitHub Actions workflow is enabled in the prepared snapshot. The inherited workflow is retained as a `.disabled` template so a push does not silently start external workflow activity. Enable it only after explicit review.
