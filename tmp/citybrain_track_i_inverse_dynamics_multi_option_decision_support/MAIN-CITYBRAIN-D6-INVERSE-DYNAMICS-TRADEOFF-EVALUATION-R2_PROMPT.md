# Prompt — MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-TRADEOFF-EVALUATION-R2

## Task

Evaluate and compare generated inverse-dynamics candidate options.

## Goal

Turn generated candidate options into comparable decision-support evidence by applying shared comparison axes, detecting dominated options, preserving do-nothing baseline, and flagging missing/unsafe/stale cases.

This is evaluation only. It does not recommend, promote, execute, dispatch, control, or certify anything.

## Required upstreams

- Track I preflight PASS
- Inverse Dynamics Generator R1 PASS
- Track S golden quality gate available
- Track B Plan Mode / SUMO closeout PASS
- Track R Similar Case Retrieval closeout PASS

## Evaluation rules

For each reviewed option set:

1. compare all options on the same `comparison_axes`
2. preserve the do-nothing baseline
3. flag dominated options
4. flag missing obvious options where golden fixture expects them
5. flag stale `valid_as_of` or `scenario_state_ref`
6. preserve abstain/no-safe-option outputs
7. ensure all tradeoffs cite evidence/simulation/similar-case refs where applicable
8. ensure all execution states remain `not_executed`

## Expected output root

`outputs/main_citybrain_d6_inverse_dynamics_tradeoff_evaluation_r2/`

## Expected files

- `MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_TRADEOFF_EVALUATION_R2_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `TRADEOFF_EVALUATION_REPORT.json`
- `TRADEOFF_EVALUATION_RESULTS.json`
- `DOMINATED_OPTION_FINDINGS.json`
- `MISSING_OPTION_FINDINGS.json`
- `STALE_STATE_FINDINGS.json`
- `GOLDEN_QUALITY_GATE_RESULTS.json`
- `OPTION_SET_SCORECARD.json`
- `VALIDATION_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

## Acceptance checks

- all option sets evaluated
- comparison axes consistent
- dominated option detection works
- missing obvious option detection works
- stale scenario detection works
- golden quality gate PASS
- do-nothing baseline preserved
- no-safe/abstain preserved
- execution_state not_executed preserved
- claim/no-action/no-mutation/secret/hash PASS

## Pass status

`PASS_MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_TRADEOFF_EVALUATION_R2_WITH_LIMITATIONS`

## Fail status

`FAIL_MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_TRADEOFF_EVALUATION_R2`
