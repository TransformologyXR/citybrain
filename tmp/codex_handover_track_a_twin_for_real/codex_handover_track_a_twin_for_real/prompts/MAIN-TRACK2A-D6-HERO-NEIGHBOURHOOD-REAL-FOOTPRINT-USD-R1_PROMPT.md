# Prompt — MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-FOOTPRINT-USD-R1

You are continuing CityBrain from the frozen D6 Hero Neighbourhood Control Room Reference Demo and related closeouts.

Task:

`MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-FOOTPRINT-USD-R1`

Purpose:

Create the first bounded real/accepted footprint USD layer for the hero neighbourhood and bind it to existing canonical/scene/operator context without promoting scene refs into canonical IDs.

Expected success status:

`PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_FOOTPRINT_USD_R1_WITH_LIMITATIONS`

Read this entire prompt before modifying anything. This task must be additive, local/replay-only, and review-context only.

## Inputs

Consume:
- Real USD Twin Preflight
- Hero Scene Pack Closeout
- R1/R2/R3 Hero asset/overlay/Kit artifacts
- CER/SEG v2 closeout
- integration-readiness review

## Work

Create a bounded USD/USDA representation of the hero neighbourhood using accepted/available footprint or footprint-like geometry from upstream artifacts.

Required:
- stable prim paths
- binding records linking prim path ↔ existing hero binding / scene ref / canonical ref where available
- explicit `binding_scope` values such as `canonical_bound`, `scene_binding_context`, `source_context`, `operator_context`, `unresolved_preserved`
- evidence and limitation refs
- unresolved/quarantined preservation
- no promotion of prim paths/source refs into canonical IDs

## Outputs

Use output root:
`outputs/main_track2a_d6_hero_neighbourhood_real_footprint_usd_r1/`

Expected files:
- `MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_FOOTPRINT_USD_R1_DECISION.json`
- `hero_neighbourhood_real_footprint_r1.usda`
- `REAL_FOOTPRINT_BINDING_REGISTRY.json`
- `REAL_FOOTPRINT_BINDING_REGISTRY.jsonl`
- `PRIM_PATH_INDEX.json`
- `EVIDENCE_AND_LIMITATION_TRACE.json`
- `UNRESOLVED_QUARANTINED_PRESERVATION_REPORT.json`
- `OMNIVERSE_HANDOFF_NOTES.md`
- `WEB_COMPANION_IMPACT.md`
- audits and hash manifest

## Validation

Validate:
- USD/USDA file exists and is deterministic text
- all prim paths are unique
- all bindings have evidence/limitation trace
- unresolved/quarantined contexts are preserved
- no scene/source/prim ref is promoted to canonical ID

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
