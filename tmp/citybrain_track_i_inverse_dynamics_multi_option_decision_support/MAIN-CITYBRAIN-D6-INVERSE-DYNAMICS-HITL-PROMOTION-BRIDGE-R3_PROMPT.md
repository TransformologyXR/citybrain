# Prompt — MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-HITL-PROMOTION-BRIDGE-R3

## Task

Create a review-only bridge from evaluated candidate options to Track D HITL proposal lifecycle references.

## Goal

Map eligible candidate options to potential Track D proposal inputs without promoting automatically and without changing Track D lifecycle state.

Track D remains authoritative for proposal approval, rejection, modification, request-more-evidence, audit, and lifecycle state.

## Required upstreams

- Inverse Dynamics Tradeoff Evaluation R2 PASS
- Track D HITL reviewed-action milestone freeze PASS
- Track S Track D composition rules PASS

## Bridge rules

- Option is not Proposal.
- `candidate_options[]` remain pre-review options.
- `proposal_refs[]` may contain proposed references only if created as review-context bridge records.
- No proposal may be marked approved.
- No execution state may change from `not_executed`.
- Track D lifecycle state must not be redefined.
- `review_state_rollup` may mirror only for display.
- Any unsafe promotion attempt must be blocked and logged.

## Expected output root

`outputs/main_citybrain_d6_inverse_dynamics_hitl_promotion_bridge_r3/`

## Expected files

- `MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_HITL_PROMOTION_BRIDGE_R3_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `HITL_PROMOTION_BRIDGE_CONTRACT.json`
- `OPTION_TO_TRACK_D_PROPOSAL_MAPPING.json`
- `PROMOTION_ELIGIBILITY_REPORT.json`
- `BLOCKED_PROMOTION_ATTEMPTS.json`
- `TRACK_D_AUTHORITY_PRESERVATION_AUDIT.json`
- `REVIEW_STATE_ROLLUP_REPORT.json`
- `VALIDATION_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

## Acceptance checks

- no automatic promotion
- no approved proposals created
- no execution state change
- Track D authority preserved
- unsafe promotion attempts blocked/logged
- claim/no-action/no-mutation/secret/hash PASS

## Pass status

`PASS_MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_HITL_PROMOTION_BRIDGE_R3_WITH_LIMITATIONS`

## Fail status

`FAIL_MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_HITL_PROMOTION_BRIDGE_R3`
