# PROMPT — MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTRACT-SPINE-CLOSEOUT

You are Codex closing Track S after S1-S4.

## Task

Close the decision-support contract spine.

Task name:

`MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTRACT-SPINE-CLOSEOUT`

Expected status on success:

`PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_WITH_LIMITATIONS`

Expected output root:

`outputs/main_citybrain_d6_decision_support_contract_spine_closeout/`

Expected runner:

`scripts/run_main_citybrain_d6_decision_support_contract_spine_closeout.py`

## Purpose

Freeze the contract spine before Plan Mode, SUMO, inverse dynamics, similar-case retrieval, or cascade work begins.

This closeout should verify and index:

- reviewed_option_set schema
- candidate_option schema
- option vs proposal composition rules
- D4Y decision-support relationship
- governed 9-stage runtime interface
- hero corridor reviewed-action enum
- golden quality gate
- boundary/no-action/no-mutation/secret/hash audits

## Required upstreams

Discover and require green outputs from:

1. `main_citybrain_d6_decision_support_option_set_contract_preflight`
2. `main_citybrain_d6_governed_9_stage_runtime_interface_preflight`
3. `main_citybrain_d6_hero_corridor_reviewed_action_enum_r1`
4. `main_citybrain_d6_decision_support_golden_quality_gate_r1`

Also discover as supporting frozen context:

- R2 certified-state and handover refresh
- Hero USD Twin HITL final package review
- HITL reviewed-action milestone freeze
- R8 edge registry hardening
- CER/SEG v2 closeout

Do not mutate any upstream.

## Expected files

- `MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTRACT_SPINE_CLOSEOUT_DECISION.json`
- `README.md`
- `INPUT_ARTIFACT_INDEX.json`
- `CONTRACT_SPINE_ACCEPTANCE_MATRIX.json`
- `CONSOLIDATED_CONTRACT_INDEX.json`
- `OPTION_SET_SCHEMA_SUMMARY.md`
- `TRACK_D_COMPOSITION_CLOSEOUT.md`
- `D4Y_DECISION_SUPPORT_CLOSEOUT.md`
- `NINE_STAGE_INTERFACE_CLOSEOUT.md`
- `HERO_CORRIDOR_ACTION_ENUM_CLOSEOUT.md`
- `GOLDEN_QUALITY_GATE_CLOSEOUT.md`
- `NEXT_TRACK_RECOMMENDATIONS.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

## Acceptance criteria

Pass only if:

- all S1-S4 required upstreams are green.
- schemas and examples are present.
- golden quality gate is present and discriminating.
- Track D composition is explicit.
- D4Y relationship is explicit.
- 9-stage interface rejects nine-LLM interpretation.
- action enum is closed and review-only.
- no execution/action state is introduced.
- boundary/no-action/no-mutation/secret/hash audits pass.

## Recommended next tasks after pass

Recommend two lanes after this closeout:

1. `MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-PREFLIGHT`
2. `MAIN-CITYBRAIN-D6-SIMILAR-CASE-RETRIEVAL-PREFLIGHT`

Do not start inverse dynamics until Plan Mode/SUMO has at least one green scenario output.
