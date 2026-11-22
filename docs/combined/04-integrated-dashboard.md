# Stage 4: integrated application

The original dashboard shell and repository, commit, prediction, feedback and history controls remain. One page now adds public-workflow discovery, explicit research-model cold preview, and all three frozen study regimes with project-level results. The archived v2 viewer remains accessible as a historical view, not the default application.

A cold preview is a new first-push scenario at the displayed cutoff, not a retrospectively successful prediction. The UI shows exact SHA, workflow, cutoff, feature contract, artifact hash and deliberately missing fields. It never silently substitutes for legacy inference, supplies live online-history mode, sends CI events, or feeds scenario results into legacy feedback.

## Checks

- Real browser, real Flask public workflow discovery and C1 preview. Raw model probability 30.23%, model cutoff 38.50%, exact commit and request-time cutoff displayed.
- All three regimes render three aggregate rows and 12/15 project-model rows, including the negative online extension result.
- Desktop 1440px and mobile 390px screenshots inspected. No whole-page horizontal overflow; tables scroll within their containers on mobile.
- Browser has no JavaScript errors; prospective preview leaves legacy feedback disabled.
- Three contract/frozen-hash tests and two raw-probability/advice tests pass.
- GitHub auto-polling removed. Provider access is explicit manual action only.

Legacy model inference is unavailable under the current mismatched artifact runtime. Local API availability is not a claim that every model is available. Stage 5 adds systematic malformed-data/loading/retry coverage. No merge or release.
