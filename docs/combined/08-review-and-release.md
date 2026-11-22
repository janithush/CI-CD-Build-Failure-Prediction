# Stage 8: attribution, thesis boundary and review handoff

## Review order

Eight stacked branches/PRs correspond to issues #1 through #8. Each contains a focused change, issue linkage and test note. Review from the earliest dependency forward. Later PRs currently target their preceding branch, so maintain the dependency order and rebase/retarget as needed only after approved merges. No merge or release is performed by this work.

1. Baseline and frozen contract.
2. Raw model probability separated from heuristic advice.
3. Strict saved-model service and explicit cold-only live preview.
4. Original dashboard extended, rather than replaced with an unrelated frozen-results page.
5. Loading/schema/error/retry handling.
6. Immutable local records, repository history and bound usefulness assessments.
7. End-to-end/parity/failure/security/visual acceptance.
8. Current setup, rights, thesis boundary and future release checklist.

See the numbered reports in this folder. Stage-7 checks were repeated after dependency alignment on the final candidate. Tests are implementation acceptance, not new experiments or revised scientific results.

## Rights and attribution

Credit remains with Shukri (mhdshukry) and original contributors for inherited work. Janith's stated verbal permission remains reported permission, not a licence to other recipients. The existing MIT grant stays limited to the four files explicitly named in LICENSING.md. No inherited file is relicensed, and the combined implementation does not silently extend the grant.

## Preserved findings

No demonstrated C1 transfer gain. Cold extension AP changes have uncertainty intervals including zero; richer online performance is worse. Warnings/false alarms can increase sharply. All nine external projects were already viewed, so the extension is exploratory. Rerun discordance and log signatures are not causal labels. The 39/5/3/40 audit strata and unavailable per-test history remain unchanged. UI integration establishes none of accuracy gain, safe CI skipping or measured developer benefit.

## Thesis boundary

No thesis file, table, result, model or scientific claim is changed here. If Janith later chooses to describe the interface, a reviewable implementation-only paragraph could explain that the post-study local application combines legacy inspection, explicit cold-start saved-model scenarios and frozen evidence, while preserving the study limitations. That paragraph must not be inserted as a new validation finding, conceal material assistance or imply that replay was prospective testing. Any thesis change is a separate request/review.

## Future release checklist, not authorization

- Obtain Janith's explicit approval to merge the reviewed stack and approve a new release.
- Resolve or explicitly retain the incompatible legacy inference gate and missing live online-history/run-outcome capability.
- Verify the exact approved revision, dependencies, full test suite, frozen hashes and redacted visual evidence.
- Keep v1.0.0 and v2.0.0 tags/releases unchanged. A future new tag must identify the combined implementation and its remaining limits; no version number is reserved by this document.
- Preserve attribution/licensing boundaries and security caveats in release notes.
- Exclude credentials, raw logs, private thesis files, operational databases and local browser evidence.
- Do not enable external CI, retraining, deployment or multi-user hosting as a side effect of release preparation.

The current result is ready for Janith's review as a local research candidate, not production readiness or thesis submission clearance.
