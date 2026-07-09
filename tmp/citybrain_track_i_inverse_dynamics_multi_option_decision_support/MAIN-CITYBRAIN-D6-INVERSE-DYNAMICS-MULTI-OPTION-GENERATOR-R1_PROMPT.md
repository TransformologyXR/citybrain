# Prompt — MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-MULTI-OPTION-GENERATOR-R1

## Task

Generate bounded local/replay candidate option sets for the shared hero corridor scenario.

## Goal

Produce review-safe inverse-dynamics candidate options from a desired outcome, using the Track S `reviewed_option_set` schema.

The output must include:
- mandatory do-nothing baseline
- 2–3 candidate interventions where possible
- abstain/no-safe-option case where applicable
- comparison axes from the option-set contract
- Track B simulation references
- Track R similar-case references
- Track D proposal mapping fields set to null unless explicitly promoted later

## Required upstreams

- Track I preflight PASS
- Track S contract spine closeout PASS
- Track B Plan Mode / SUMO closeout PASS
- Track R Similar Case Retrieval closeout PASS
- Track D HITL freeze PASS

## Generation rules

This R1 may use deterministic fixture generation and bounded local replay data.

It must not:
- execute any action
- promote an option into Track D proposal lifecycle
- call live routing/control systems
- create official cases/tickets
- publish alerts
- make certified recommendations

## Required option-set behavior

Every `reviewed_option_set` with `option_set_outcome = options_available` must include:

- `do_nothing_baseline_option_id`
- at least one `option_role = do_nothing_baseline`
- one or more `candidate_intervention` options
- `execution_state = not_executed`
- `human_review_required = true`
- `proposal_refs = []` unless a later Track D bridge maps it
- `similar_case_refs[]` from Track R when available
- `simulation_refs[]` from Track B when available

At least one generated fixture must exercise:

- options available
- no safe reviewed option
- insufficient evidence or simulation unavailable
- blocked unsafe action

## Expected output root

`outputs/main_citybrain_d6_inverse_dynamics_multi_option_generator_r1/`

## Expected files

- `MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_MULTI_OPTION_GENERATOR_R1_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `INVERSE_DYNAMICS_OPTION_SET_SCHEMA_BINDING.json`
- `GENERATED_REVIEWED_OPTION_SETS.json`
- `GENERATED_REVIEWED_OPTION_SETS.jsonl`
- `OPTION_GENERATION_TRACE.json`
- `SIMULATION_REF_ATTACHMENT_REPORT.json`
- `SIMILAR_CASE_ATTACHMENT_REPORT.json`
- `UNSAFE_ACTION_BLOCK_REPORT.json`
- `VALIDATION_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

## Acceptance checks

- reviewed_option_set schema validation PASS
- candidate_option schema validation PASS
- do-nothing baseline PASS
- abstain/no-safe-option PASS
- execution_state not_executed PASS
- no Track D promotion PASS
- unsafe action blocked PASS
- claim/no-action/no-mutation/secret/hash PASS

## Pass status

`PASS_MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_MULTI_OPTION_GENERATOR_R1_WITH_LIMITATIONS`

## Fail status

`FAIL_MAIN_CITYBRAIN_D6_INVERSE_DYNAMICS_MULTI_OPTION_GENERATOR_R1`
