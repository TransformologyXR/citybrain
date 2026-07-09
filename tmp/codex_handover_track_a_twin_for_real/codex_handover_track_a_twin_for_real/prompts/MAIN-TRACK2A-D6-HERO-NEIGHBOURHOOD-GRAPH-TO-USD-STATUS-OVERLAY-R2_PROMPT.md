# Prompt — MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-GRAPH-TO-USD-STATUS-OVERLAY-R2

You are continuing CityBrain from the frozen D6 Hero Neighbourhood Control Room Reference Demo and related closeouts.

Task:

`MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-GRAPH-TO-USD-STATUS-OVERLAY-R2`

Purpose:

Project review-safe graph/event/relationship status onto the bounded USD layer as metadata and overlay packets.

Expected success status:

`PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_GRAPH_TO_USD_STATUS_OVERLAY_R2_WITH_LIMITATIONS`

Read this entire prompt before modifying anything. This task must be additive, local/replay-only, and review-context only.

## Inputs

Consume:
- Real Footprint USD R1
- R7/R8 edge registry
- CER/SEG v2 relationship ontology and review-state contracts
- Incident Mode operator-surface handoff R4
- Hero Event Overlay R2 / Kit Handoff R3 if present

## Work

Create a graph-to-USD status overlay that colors/tags hero prims by review-safe context.

Allowed status examples:
- `review_context_active`
- `event_replay_context`
- `operator_review_context`
- `unresolved_preserved`
- `quarantined_preserved`
- `scene_binding_context`
- `limited_evidence_context`

Do not use:
- `confirmed_incident`
- `violation`
- `legal`
- `certified`
- `dispatched`
- `controlled`
- `enforced`

## Outputs

Use output root:
`outputs/main_track2a_d6_hero_neighbourhood_graph_to_usd_status_overlay_r2/`

Expected files:
- `MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_GRAPH_TO_USD_STATUS_OVERLAY_R2_DECISION.json`
- `GRAPH_TO_USD_STATUS_OVERLAY.json`
- `GRAPH_TO_USD_STATUS_OVERLAY.jsonl`
- `hero_neighbourhood_status_overlay_r2.usda`
- `STATUS_OVERLAY_LEGEND.json`
- `CERSEG_COMPATIBILITY_REPORT.json`
- `OPERATOR_SURFACE_ALIGNMENT_REPORT.json`
- `WEB_COMPANION_ALIGNMENT_REPORT.json`
- audits and hash manifest

## Validation

Pass only if:
- overlay statuses use approved review-safe enums
- CER/SEG v2 compatibility passes
- no legal/certified/action status appears
- evidence/limitation trace is complete

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
