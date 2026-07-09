# Prompt — MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-MULTI-OPTION-CLOSEOUT

## Task

Close out the inverse-dynamics multi-option decision-support lane.

## Goal

Verify that preflight, generator, tradeoff evaluation, and HITL promotion bridge all passed and that the lane preserves the review-only boundary.

## Required upstreams

- Inverse Dynamics Preflight PASS
- Generator R1 PASS
- Tradeoff Evaluation R2 PASS
- HITL Promotion Bridge R3 PASS
- Track S PASS
- Track B PASS
- Track R PASS
- Track D PASS

## Closeout checks

Verify:

- all required upstreams found and green
- reviewed option sets produced
- do-nothing baseline preserved
- abstain/no-safe-option preserved
- tradeoff evaluation PASS
- golden quality gate PASS
- similar-case refs attached where applicable
- simulation refs attached where applicable
- Track D bridge preserves authority
- no execution, dispatch, control, enforcement, legal, certified, or automated-action claim
- no production/public API claim
- all JSON/JSONL parse cleanly
- all hash manifests verify
- local open index exists
- no mutation and secret audits pass

## Expected output root

`outputs/main_citybrain_d6_inverse_dynamics_multi_option_closeout/`

## Expected files

- `MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_MULTI_OPTION_CLOSEOUT_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `ACCEPTANCE_MATRIX.json`
- `OPTION_SET_CLOSEOUT_SUMMARY.json`
- `TRADEOFF_CLOSEOUT_SUMMARY.json`
- `HITL_BRIDGE_CLOSEOUT_SUMMARY.json`
- `QUALITY_GATE_CLOSEOUT_SUMMARY.json`
- `BOUNDARY_AND_LIMITATION_REGISTER.md`
- `NEXT_TASK_RECOMMENDATION.md`
- `VALIDATION_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

## Pass status

`PASS_MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_MULTI_OPTION_CLOSEOUT_WITH_LIMITATIONS`

## Fail status

`FAIL_MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_MULTI_OPTION_CLOSEOUT`

## Recommended next task after pass

`MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-MULTI-OPTION-MILESTONE-FREEZE`

Alternative next task if freeze is skipped:

`MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-CONTRACT-SMOKE-R1`
