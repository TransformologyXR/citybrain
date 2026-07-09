# MAIN-CITYBRAIN-D6-RUNTIME-TRACE-DEMO-POLISH-FINAL-PACKAGE-REVIEW

## Objective

Review the combined runtime trace + demo polish package for final sprint packaging quality, factual consistency, claim-label consistency, and outward narrative safety.

This is packaging/review only. No new feature implementation.

## Required upstreams

Require green:

- `MAIN-CITYBRAIN-D6-RUNTIME-TRACE-DEMO-POLISH-INTEGRATION-READINESS-REVIEW`
- governed runtime trace harness closeout/freeze
- decision-support demo polish closeout/freeze
- latest decision-support certified-state/handover refresh

## Required checks

Validate:

- Counts and facts are consistent across runtime trace harness, demo polish, prior decision-support handover, and integration-readiness review.
- Collateral/demo language is aligned with the frozen technical facts.
- Claim labels are present and accurate.
- Limitations are disclosed, including review-only context, no-action boundaries, non-blocking gaps, and any artifact/package visual-review limitations.
- Operator-facing story does not imply execution, dispatch, enforcement, monitoring, legal/certified findings, or production/public API readiness.
- The package explicitly distinguishes trace harness from runtime execution and demo polish from new capability.

## Expected output root

`outputs/main_citybrain_d6_runtime_trace_demo_polish_final_package_review/`

## Expected files

- `MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_FINAL_PACKAGE_REVIEW_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `FINAL_PACKAGE_RECONCILIATION_MATRIX.json`
- `FACT_COUNT_RECONCILIATION.json`
- `CLAIM_LABEL_REVIEW.json`
- `LIMITATION_DISCLOSURE_REVIEW.json`
- `OPERATOR_NARRATIVE_SAFETY_REVIEW.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

## PASS status

`PASS_MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_FINAL_PACKAGE_REVIEW_WITH_LIMITATIONS`

## FAIL status

`FAIL_MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_FINAL_PACKAGE_REVIEW`
