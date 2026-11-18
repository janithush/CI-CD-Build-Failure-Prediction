# Version 2 research bundle

This directory is a frozen historical research record, not a live prediction replacement.

## Quick reproduction

Use Python 3.10 or a compatible environment. The original replay environment used:

```text
numpy==2.2.6
pandas==2.3.3
scikit-learn==1.7.2
xgboost==3.2.0
joblib==1.6.0
```

Install `requirements.txt` in a virtual environment, then from the repository root:

```bash
python research/v2/reproduce.py verify
python research/v2/reproduce.py replay
python research/v2/reproduce.py refit --output research-v2-refit
```

- `verify` recalculates all 42 project/model/regime metric rows and macro summaries from the saved row-level probabilities. It does not load pickles or access the network.
- `replay` loads the six supplied fitted research models, scores the frozen feature tables, applies the original online route and checks all nine probability vectors against saved predictions. Only load these trusted artifacts after checking their hashes. Pickle/joblib can execute code.
- `refit` uses source rows only, enforces the original whole-commit and label-maturity stages, tries the original six learned settings, calibrates and selects thresholds on separate source stages, and writes a new output directory. It never replaces the frozen files. It checks selected settings/thresholds; numerical reproducibility also depends on the recorded environment.

No command in this portable entry point recollects provider data, triggers CI, sends feedback, deploys a model or changes a remote repository. New experiments on these already-viewed targets are not untouched confirmation.

## Directory map

- `data/`: gzip-compressed frozen features, predictions, source manifest, rerun evidence and log-signature pointers. Source-feature tables contain retrospective recorded-availability inputs, not certified real-time observations.
- `models/`: original B0/C1 history/no-history models and the two extended branches, with source-only metadata for the extended branches.
- `results/`: fixed protocol, before/after report, all project metrics, reliability bins, feature contract and saved verification outcomes.
- `src/`: portable strict training helpers. `improvement_inner.py` differs from the archived execution copy only in the relative location used to import the strict trainer.
- `records/noncode/`: credential-free archival copies of the executed scientific scripts. They retain the original study directory layout and are **not standalone portable commands**. In particular, they expect provider caches and previous-study inputs that are not in this repository. Use `reproduce.py` for supported portable reproduction.
- `records/final-four/` and `records/repair/`: earlier confirmation and repair protocols/results retained as separate studies, not pooled into one score.

The full provider recollection and raw-log audit need the original private evidence archives and their restore layout. Raw CI ZIP logs, complete provider payload caches, private dissertation files and personal notes are deliberately excluded here. This repository supports frozen-feature model replay and source-only extended refitting; it does not claim raw-source-to-result independence without those private archive dependencies.

## Scientific interpretation

B0 already contains workflow/repository/branch failure history and run-start clock fields, despite the old `commit_*` names. C1 adds 13 change-context descriptors. The extension adds 17 static clock/attempt/OS/matrix declaration descriptors and six released-evidence history descriptors. OS/matrix fields describe declarations, not fully resolved runtime execution.

The primary endpoint is broad provider success/failure. Rerun discordance and log signatures are not causal code/non-code labels. Four original raw-log 404s and one oversized parse exclusion remain unknown. A consistent per-test ledger is unavailable. All failure strata, no-gain results and worse online/warning results are retained.

The constant-source and selected-subset analyses in earlier records are descriptive, not replacements for the primary external comparison. Saved thresholds are not validated operational cutoffs. No user-time saving, safe skipping, universal transfer or independent human label validation is claimed.

## Provenance and integrity

`FILES_SHA256.json` at the repository root covers the prepared deliverable files except itself and local test outputs. The original exact execution artifacts and pre-score freeze hashes remain in the private research archive. New portable code has its own hashes; it must not be represented as byte-identical to the original execution code.

The thesis and other manuscripts are not bundled. Publication of the frozen bundle does not imply that the v2 service is operationally deployed. Any later deployment must be documented separately rather than rewriting the evaluated experiments.
