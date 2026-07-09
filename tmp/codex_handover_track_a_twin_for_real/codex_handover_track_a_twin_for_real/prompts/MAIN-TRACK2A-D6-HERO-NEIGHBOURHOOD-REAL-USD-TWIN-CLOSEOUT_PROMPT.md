# Prompt — MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-USD-TWIN-CLOSEOUT

You are continuing CityBrain from the frozen D6 Hero Neighbourhood Control Room Reference Demo and related closeouts.

Task:

`MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-USD-TWIN-CLOSEOUT`

Purpose:

Close the Track A real-USD Hero Neighbourhood twin lane as a bounded, non-certified, local/replay control-room spatial proof.

Expected success status:

`PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_CLOSEOUT_WITH_LIMITATIONS`

Read this entire prompt before modifying anything. This task must be additive, local/replay-only, and review-context only.

## Inputs

Require green:
- Preflight
- Real Footprint USD R1
- Graph-to-USD Status Overlay R2
- Replay Event Route Animation R3

## Work

Create a closeout package that confirms the lane is complete, bounded, and honest.

## Outputs

Use output root:
`outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_closeout/`

Expected files:
- `MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_CLOSEOUT_DECISION.json`
- `ACCEPTANCE_MATRIX.json`
- `UPSTREAM_STATUS_SUMMARY.json`
- `USD_LAYER_REVIEW.json`
- `GRAPH_TO_USD_OVERLAY_REVIEW.json`
- `REPLAY_ANIMATION_REVIEW.json`
- `OMNIVERSE_KIT_COMPOSER_HANDOFF_REVIEW.json`
- `WEB_COMPANION_ALIGNMENT_REVIEW.json`
- `LIMITATIONS_LEDGER.md`
- audits and hash manifest

## Pass criteria

Pass only if:
- all required upstream tasks are green
- acceptance matrix passes
- no blocking gaps
- non-blocking gaps are logged
- no citywide/certified twin claim appears

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
