# MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-PREFLIGHT

Objective: preflight a bounded Plan Mode + SUMO forward-dynamics lane that consumes the Track S `reviewed_option_set` contract and the shared hero corridor scenario.

This is not a full runtime build and not inverse dynamics. It defines exactly what Plan Mode/SUMO may consume and emit.

Required upstreams:
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTRACT-SPINE-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-R2-CERTIFIED-STATE-AND-HANDOVER-REFRESH`
- `MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-MILESTONE-FREEZE-R2`
- `MAIN-CITYBRAIN-D6-HITL-REVIEWED-ACTION-MILESTONE-FREEZE`

Supporting upstreams:
- R8 edge registry hardening
- CER/SEG v2 closeout
- Hero USD Twin HITL integration readiness
- Track A real USD twin freeze

Output root:
`outputs/main_citybrain_d6_plan_mode_sumo_preflight/`

Runner:
`scripts/run_main_citybrain_d6_plan_mode_sumo_preflight.py`

Produce:
- `MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_PREFLIGHT_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `TRACK_S_CONTRACT_CONSUMPTION_REPORT.json`
- `SUMO_AVAILABILITY_AND_LIMITATIONS_REPORT.json`
- `SHARED_HERO_SCENARIO_BINDING.json`
- `PLAN_MODE_STAGE_INTERFACE_PLAN.json`
- `REVIEWED_OPTION_SET_EMISSION_PLAN.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

Acceptance:
- required upstreams found and green
- Track S schemas discovered or summarized from output artifacts
- SUMO source/fixtures/preexisting scripts discovered or explicit bounded fallback recorded
- shared hero scenario selected exactly once
- execution remains simulation/local/replay only
- no candidate option promoted to Track D proposal
- no external action, no dispatch, no control

Success status:
`PASS_MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_PREFLIGHT_WITH_LIMITATIONS`

Failure status:
`FAIL_MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_PREFLIGHT`

Boundary is load-bearing: local/replay review/query context only. No production/public API claim, no autonomous monitoring, no alerts, no dispatch, no routing/control, no enforcement, no ticket/case creation, no legal/certified/confirmed finding, no automated action, no citywide certified twin, no certified physical geometry claim, and no model/LLM in the deterministic truth path unless a later bounded narration gate explicitly allows it.
