# MAIN-CITYBRAIN-D6-PLAN-MODE-RUNTIME-SMOKE-R3

Objective: smoke the governed Plan Mode path using the Track S runtime interface and the normalized option-set outputs.

This is a thin governed state-machine smoke, not a full 9-stage implementation and not nine LLM gates.

Required upstreams:
- `MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-INTERFACE-PREFLIGHT` from Track S
- `MAIN-CITYBRAIN-D6-PLAN-MODE-OPTION-SET-NORMALIZATION-R2`

Output root:
`outputs/main_citybrain_d6_plan_mode_runtime_smoke_r3/`

Runner:
`scripts/run_main_citybrain_d6_plan_mode_runtime_smoke_r3.py`

Produce:
- `MAIN_CITYBRAIN_D6_PLAN_MODE_RUNTIME_SMOKE_R3_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `GOVERNED_STAGE_SMOKE_TRACE.json`
- `STAGE_INPUT_OUTPUT_MATRIX.json`
- `OPTION_SET_RUNTIME_QUERY_RESULTS.json`
- `QUALITY_GATE_REPLAY_REPORT.json`
- `TRACK_D_BOUNDARY_CARRY_FORWARD.json`
- `MODEL_USAGE_AUDIT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

Stage smoke semantics:
- RECALL reads frozen state and scenario refs
- PLAN selects the bounded Plan/SUMO workflow
- VALIDATE_PLAN checks schema/guardrail prerequisites
- EXECUTE runs local simulation/fixture retrieval only, not real-world action
- NORMALIZE emits reviewed_option_set
- SYNTHESIZE may be deterministic or one grounded narration placeholder; no ungrounded truth path
- RESOLVE_ACTIONS maps option roles and possible Track D promotion eligibility only; no promotion/execution
- SUGGEST surfaces safe next-look/review-only option sets
- COMPLETE writes trace/audit/limitations

Acceptance:
- every stage has explicit input/output or is marked thin/stubbed
- no autonomous LLM chain
- no execution beyond local replay/sim fixture
- no Track D proposal created or promoted

Success status:
`PASS_MAIN_CITYBRAIN_D6_PLAN_MODE_RUNTIME_SMOKE_R3_WITH_LIMITATIONS`

Failure status:
`FAIL_MAIN_CITYBRAIN_D6_PLAN_MODE_RUNTIME_SMOKE_R3`

Boundary is load-bearing: local/replay review/query context only. No production/public API claim, no autonomous monitoring, no alerts, no dispatch, no routing/control, no enforcement, no ticket/case creation, no legal/certified/confirmed finding, no automated action, no citywide certified twin, no certified physical geometry claim, and no model/LLM in the deterministic truth path unless a later bounded narration gate explicitly allows it.
