# Prompt — MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REPLAY-EVENT-ROUTE-ANIMATION-R3

You are continuing CityBrain from the frozen D6 Hero Neighbourhood Control Room Reference Demo and related closeouts.

Task:

`MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REPLAY-EVENT-ROUTE-ANIMATION-R3`

Purpose:

Create a deterministic replay-event and route/context animation handoff for the shared hero scenario.

Expected success status:

`PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REPLAY_EVENT_ROUTE_ANIMATION_R3_WITH_LIMITATIONS`

Read this entire prompt before modifying anything. This task must be additive, local/replay-only, and review-context only.

## Inputs

Consume:
- Graph-to-USD Status Overlay R2
- Incident Mode evidence/operator packets
- D5/D6 local running state
- R7/R8 edges
- CER/SEG v2 contracts

## Work

Build a deterministic animation handoff, not an interactive production system.

Represent:
- replay event appears
- affected hero prim/status changes
- route/corridor context is highlighted
- unresolved/quarantined contexts remain visible as limited/review context
- evidence/limitation refs remain accessible

The animation can be a frame manifest, timeline JSON, USDA metadata sequence, or all three.

## Outputs

Use output root:
`outputs/main_track2a_d6_hero_neighbourhood_replay_event_route_animation_r3/`

Expected files:
- `MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REPLAY_EVENT_ROUTE_ANIMATION_R3_DECISION.json`
- `REPLAY_EVENT_ROUTE_ANIMATION_TIMELINE.json`
- `REPLAY_EVENT_ROUTE_ANIMATION_FRAMES.jsonl`
- `hero_neighbourhood_replay_event_route_animation_r3.usda`
- `OPERATOR_WALKTHROUGH_NOTES.md`
- `EXECUTIVE_WALKTHROUGH_NOTES.md`
- `EVIDENCE_AND_LIMITATION_TRACE.json`
- audits and hash manifest

## Validation

Pass only if:
- timeline is deterministic
- animation references the shared scenario
- no autonomous monitoring claim exists
- no route/control or dispatch action is implied
- limitation labels appear in operator/executive notes

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
