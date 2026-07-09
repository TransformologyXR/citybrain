# Prompt — MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-USD-TWIN-PREFLIGHT

You are continuing CityBrain from the frozen D6 Hero Neighbourhood Control Room Reference Demo and related closeouts.

Task:

`MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-USD-TWIN-PREFLIGHT`

Purpose:

Define the bounded real-USD Hero Neighbourhood twin plan. This is a preflight only: discover upstream artifacts, choose the accepted footprint/source geometry strategy, lock scope, define outputs, and validate that the track can proceed without making citywide/certified twin claims.

Expected success status:

`PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_PREFLIGHT_WITH_LIMITATIONS`

Read this entire prompt before modifying anything. This task must be additive, local/replay-only, and review-context only.

## Upstream discovery

Find and index the latest green outputs for:
- `MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1`
- `MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT`
- `MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW`
- `MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT`
- `MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4`
- `MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT`
- R7/R8 edge registry artifacts

If required upstreams are missing, fail safely.

## Scope to lock

Use the shared scenario:
`HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001`

Define:
- hero neighbourhood bounds
- accepted footprint source strategy
- USD/USD-A layer strategy
- entity/scene binding strategy
- graph-to-USD status overlay strategy
- replay-event/route animation strategy
- visual acceptance method
- no-citywide/no-certified-twin labels

## Outputs

Use output root:
`outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_preflight/`

Expected files:
- `MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_PREFLIGHT_DECISION.json`
- `README.md`
- `INPUT_ARTIFACT_INDEX.json`
- `SHARED_SCENARIO_BINDING_PLAN.json`
- `REAL_FOOTPRINT_SOURCE_STRATEGY.json`
- `USD_LAYER_PLAN.json`
- `GRAPH_TO_USD_OVERLAY_PLAN.json`
- `REPLAY_EVENT_ROUTE_ANIMATION_PLAN.json`
- `ACCEPTANCE_MATRIX.json`
- audits and hash manifest

## Pass criteria

Pass only if:
- upstreams are discovered
- scope is bounded
- scenario contract is referenced
- no citywide/certified twin claim exists
- no mutation occurs

## Boundary

Preserve all existing boundaries.

Do not claim or create:
- production readiness
- public API readiness
- live autonomous monitoring
- alerts
- dispatch
- routing/control
- enforcement
- official ticket/case creation
- legal/certified findings
- citywide certified twin
- automated action
- mutation of frozen upstream outputs

All event/state/action/twin context remains local/replay review/query context only.

## Required audits

Produce:
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

Fail if a forbidden claim/action/mutation appears.
