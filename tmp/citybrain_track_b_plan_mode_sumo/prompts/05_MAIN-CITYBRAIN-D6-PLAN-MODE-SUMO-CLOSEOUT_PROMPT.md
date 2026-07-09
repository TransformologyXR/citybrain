# MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-CLOSEOUT

Objective: close the Plan Mode/SUMO forward-dynamics lane and decide whether inverse dynamics is unblocked.

Required upstreams:
- `MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-PREFLIGHT`
- `MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-SCENARIO-R1`
- `MAIN-CITYBRAIN-D6-PLAN-MODE-OPTION-SET-NORMALIZATION-R2`
- `MAIN-CITYBRAIN-D6-PLAN-MODE-RUNTIME-SMOKE-R3`

Output root:
`outputs/main_citybrain_d6_plan_mode_sumo_closeout/`

Runner:
`scripts/run_main_citybrain_d6_plan_mode_sumo_closeout.py`

Produce:
- `MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_CLOSEOUT_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `PLAN_MODE_ACCEPTANCE_MATRIX.json`
- `SUMO_SCENARIO_REVIEW.json`
- `OPTION_SET_NORMALIZATION_REVIEW.json`
- `RUNTIME_SMOKE_REVIEW.json`
- `INVERSE_DYNAMICS_READINESS_ASSESSMENT.json`
- `SIMULATION_LIMITATIONS_LEDGER.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

Acceptance:
- all upstream tasks green or fail safely
- at least one reviewed_option_set produced and validated
- do-nothing baseline present or no-safe-option represented
- local/replay simulation limitations explicit
- inverse dynamics only recommended if at least one green scenario output exists

Success status:
`PASS_MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_CLOSEOUT_WITH_LIMITATIONS`

Failure status:
`FAIL_MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_CLOSEOUT`

Recommended next if green:
`MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-MULTI-OPTION-DECISION-SUPPORT-PREFLIGHT`

Parallel/independent lane remains:
`MAIN-CITYBRAIN-D6-SIMILAR-CASE-RETRIEVAL-PREFLIGHT`

Boundary is load-bearing: local/replay review/query context only. No production/public API claim, no autonomous monitoring, no alerts, no dispatch, no routing/control, no enforcement, no ticket/case creation, no legal/certified/confirmed finding, no automated action, no citywide certified twin, no certified physical geometry claim, and no model/LLM in the deterministic truth path unless a later bounded narration gate explicitly allows it.
