# Bounded blinded AI label/source audit

18 November 2026.

## Method to include in the dissertation

A separate AI review session was started without the previous study discussion. The reviewer was asked to act as a senior software-engineering researcher and was given only a blinded evidence pack: case identifiers, repository/run/attempt identifiers, provider run records, paginated job and step records, deterministic raw log excerpts, the review rules and an empty review form. The pack withheld the study's previous inferred failure categories, prior checkout-comparison annotations, model predictions, performance tables and conclusions. The provider's own broad success/failure value remained visible because it was source evidence to be checked, not the inferred label being concealed. The reviewer used the supplied pack only and returned one locked response per case before the comparison key was opened for reconciliation. The key already existed but was withheld; the reviewer's note that it did not yet exist is not adopted here.

The review assessed broad outcome, job completeness, executed-test and assertion support, failure stage/class, observed checkout relationship and confidence, using exact evidence pointers. Missing coverage remained unknown. A helper checkout was not treated as proof of tested source. This was a bounded AI consistency review, not independent human validation.

The planned core sampled up to five successes and five failures per project from the already-fixed 500-attempt evidence cohort using seed 42, without model-score selection. Django had only three eligible failures in that evidence cohort, so the actual core contains 48 cases: 23 failures and 25 successes. Ten additional missing/ambiguous-evidence cases form a deliberately selected supplement. Total reviewed: 58. A procedural headcount error in the review instructions described 50 core plus eight supplementary cases; the authoritative sample.csv and locked output contain the actual 48 plus ten. The error is disclosed and no cases were silently replaced. Neither the core's balanced design nor the purposive supplement estimates population prevalence.

For each case, the evidence collector retrieved provider records anew. Log excerpts retained the final 80 lines per entry and diagnostic/checkout matches with context, capped at 600 lines per entry; expanded archives over the prior 100 MiB bound were not parsed. The excerpts are not full logs. Fresh retrieval can expose evidence not captured by an earlier parser or attempt export, so annotation disagreement is not automatically reviewer error or proof the old broad endpoint was wrong.

After the review was locked, its answers were joined to the withheld key. Previous and new annotations were both preserved. Reconciliation inspected exact provider failed-step records and raw test-summary excerpts for all twelve failure-class disagreements. No model was refitted, threshold changed or primary broad endpoint rescored to exploit the audit. The reconciler knew the study's existing results, so only the first AI pass was blinded. The audit supports bounded consistency checks and more cautious annotations, not an independent human validation of all 2,500 rows.

## Results

- Broad provider success/failure agrees in all 58 cases. This is a consistency check of records, not independent ground truth about source-code defects.
- Failure-class agreement is 43/48 in the stratified core and 3/10 in the uncertainty supplement: 46/58 overall. Report the strata separately; the selected supplement intentionally concentrates difficult evidence.
- Observed checkout-comparison agreement is 48/48 in the core and 10/10 in the supplement. Agreement concerns observed checkout references only, not full runtime attestation. Merge refs and helper checkouts need qualification.
- Reviewer confidence: 34 high, 15 medium, nine low. Missing failing-job logs, empty or contradictory job/step records, and incomplete checkout evidence limit the judgments.
- Assertion support is kept as yes/no/unknown. Unknown is not converted to no and is not counted as a successful agreement. The CSV preserves every comparison.

## Disagreements and handling

Six successful cases (005, 011, 023, 028, 046, 047) changed from success without verified test execution to executed-test success. The new excerpts contain actual passing test summaries. This adds evidence of some test execution, not proof that every job or test executed; case 028 still has empty step lists in most returned jobs. Keep the broad success outcome and record the new evidence, retaining the historical annotation separately.

Five previously unresolved failures (008, 026, 038, 042, 054) were called other failure by the AI reviewer. Exact provider metadata supports non-test stages: spelling/type checks, container creation, checkout, and build/environment steps. Some failing-job logs remain absent, and case 054 has no log entries at all. Record the observed non-test stage, but do not promote all five to a definitive exhaustive cause label. Retain unresolved-cause flags where full failed-job evidence is missing. The primary workflow-failure label remains unchanged.

Case 044 changed from mixed test/other failure to test-execution-only. The provider failed steps are named test steps; excerpts include a collection/import error. A test step name and collection error do not establish an assertion failure or a pure source defect, and excerpt coverage is partial. Preserve the disagreement and mark the narrow classification unresolved instead of forcing either label for a favourable result.

## Limits

This is a single fresh AI pass over bounded excerpts, with shared-model/system-bias risk, not independent human review. The supplied records have missing logs, timestamp anomalies and occasional workflow/job contradictions. High agreement on provider outcomes or checkout strings does not establish correct causal failure labels, complete source identity, safe skipping or operational benefit. The original primary results and their negative C1 finding are not replaced by an audit-selected subset.
