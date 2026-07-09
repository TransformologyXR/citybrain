# MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-SCENARIO-R1

Objective: create one bounded local/replay SUMO-compatible scenario for `scenario:HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001`.

The scenario must be sufficient to produce forward-dynamics evidence for option-set normalization. It must not claim certified traffic modeling.

Required upstream:
- `MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-PREFLIGHT`

Output root:
`outputs/main_citybrain_d6_plan_mode_sumo_scenario_r1/`

Runner:
`scripts/run_main_citybrain_d6_plan_mode_sumo_scenario_r1.py`

Produce:
- `MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_SCENARIO_R1_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `HERO_CORRIDOR_SUMO_SCENARIO_SPEC.json`
- `SCENARIO_NETWORK_OR_FIXTURE_SUMMARY.json`
- `SCENARIO_INPUT_EVENTS.jsonl`
- `SCENARIO_RUN_RESULTS.json`
- `SCENARIO_METRICS.json`
- `DO_NOTHING_BASELINE_SIMULATION.json`
- `SIMULATION_LIMITATIONS.json`
- `TRACE_AUDIT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

Minimum scenario requirements:
- same shared hero scenario
- one lane-blockage/corridor event input
- one do-nothing baseline output
- at least one candidate review intervention class from the Track S allowed-action enum, if a bounded fixture can support it
- all simulation outputs labeled local/replay context
- preserve limitations if using fixture/synthetic routeability rather than real SUMO network

Acceptance:
- scenario produced or explicit fail-safe if unavailable
- do-nothing baseline simulated or fixture-generated
- no certified traffic, routing, or control claim
- no real-world execution

Success status:
`PASS_MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_SCENARIO_R1_WITH_LIMITATIONS`

Failure status:
`FAIL_MAIN_CITYBRAIN_D6_PLAN_MODE_SUMO_SCENARIO_R1`

Boundary is load-bearing: local/replay review/query context only. No production/public API claim, no autonomous monitoring, no alerts, no dispatch, no routing/control, no enforcement, no ticket/case creation, no legal/certified/confirmed finding, no automated action, no citywide certified twin, no certified physical geometry claim, and no model/LLM in the deterministic truth path unless a later bounded narration gate explicitly allows it.
