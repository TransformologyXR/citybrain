# MAIN-CITYBRAIN-D6-PLAN-MODE-OPTION-SET-NORMALIZATION-R2

Objective: normalize Plan Mode/SUMO scenario outputs into Track S `reviewed_option_set` objects.

This task creates review-only decision-support objects. It does not create Track D proposals and does not execute anything.

Required upstreams:
- `MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-SCENARIO-R1`
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTRACT-SPINE-CLOSEOUT`

Output root:
`outputs/main_citybrain_d6_plan_mode_option_set_normalization_r2/`

Runner:
`scripts/run_main_citybrain_d6_plan_mode_option_set_normalization_r2.py`

Produce:
- `MAIN_CITYBRAIN_D6_PLAN_MODE_OPTION_SET_NORMALIZATION_R2_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `NORMALIZATION_RULES.json`
- `REVIEWED_OPTION_SETS.json`
- `REVIEWED_OPTION_SETS.jsonl`
- `OPTION_SET_SCHEMA_VALIDATION_REPORT.json`
- `DO_NOTHING_BASELINE_VALIDATION.json`
- `ABSTAIN_OUTCOME_VALIDATION.json`
- `COMPARISON_AXES_VALIDATION.json`
- `GENERATOR_SIMULATION_PROVENANCE_REPORT.json`
- `VALID_AS_OF_AND_STALENESS_REPORT.json`
- `TRACK_D_PROMOTION_BOUNDARY_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

Acceptance:
- every option set validates against Track S schema
- every candidate option validates against candidate option schema
- `execution_state` is `not_executed`
- human review required is true
- do-nothing baseline present where options are available
- abstain/no-safe-option represented where appropriate
- comparison axes consistent across options in a set
- simulation provenance and valid_as_of recorded
- proposal refs remain empty/null unless explicitly a pre-promotion reference; Track D owns lifecycle state

Success status:
`PASS_MAIN_CITYBRAIN_D6_PLAN_MODE_OPTION_SET_NORMALIZATION_R2_WITH_LIMITATIONS`

Failure status:
`FAIL_MAIN_CITYBRAIN_D6_PLAN_MODE_OPTION_SET_NORMALIZATION_R2`

Boundary is load-bearing: local/replay review/query context only. No production/public API claim, no autonomous monitoring, no alerts, no dispatch, no routing/control, no enforcement, no ticket/case creation, no legal/certified/confirmed finding, no automated action, no citywide certified twin, no certified physical geometry claim, and no model/LLM in the deterministic truth path unless a later bounded narration gate explicitly allows it.
