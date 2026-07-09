# MAIN-CITYBRAIN-D9-CHECK-GUARDRAIL-AND-SOURCE-DEPTH-R6

Implement Check as a first-class product mode.

## Check types

- claim boundary check
- source-depth check
- no-action boundary check
- unsupported impact/causality check
- missing field/source record check
- story-query duplicate-shape check if story queue is in view
- external validation/media availability check

## Required examples

- Check Wood Lane answer/brief for proximity-not-causality boundary.
- Check NYC cascade answer/brief for candidate tax-lot and response-resource limitations.
- Check Recall cutaway for generic match reasons.
- Check Diff and Perception readiness and return deferred/partial, not green.

## Required artifacts

- `D9_CHECK_RULESET.json`
- `D9_CHECK_SAMPLE_RESULTS.json`
- `D9_CHECK_SOURCE_DEPTH_LEDGER.json`
- `D9_CHECK_GUARDRAIL_AND_SOURCE_DEPTH_R6_DECISION.json`
- audits + hash manifest

Expected status:
`PASS_MAIN_CITYBRAIN_D9_CHECK_GUARDRAIL_AND_SOURCE_DEPTH_R6_WITH_LIMITATIONS`
