# TASK: HELSINKI-KIT-OBJECT-PICK-MANUAL-ALIGNMENT-R2

## Purpose
Promote the Helsinki USD/CER sidecar smoke from generic sidecar packets into a small manual object-pick alignment packet suitable for Kit/Composer review. This task proves a bounded manual alignment workflow, not automated full-scene object matching.

## Context
Prior Helsinki tasks completed:
- D4 landing: semantic CityGML identity spine landed.
- D4 consumption prep: 2,980/2,980 CityGML buildings consumed; 2,980 CER candidate map rows; 2,980 USD/CER sidecar candidate rows; visual mesh remains `VISUAL_BACKDROP_ONLY`.
- D8 parallel prompt pack: 20 USD/CER sidecar smoke packets plus a lightweight USDA handoff layer.

This R2 task should pick a small, reviewable subset and define manual alignment evidence for Kit/Composer.

## Inputs
Use existing outputs if present:
- outputs/d4_helsinki_kalasatama_context_consumption_prep_r1/
- outputs/d4_helsinki_kalasatama_usd_sidecar_alignment_smoke_r1/ or equivalent Helsinki sidecar smoke output
- CityGML identity normalization CSV
- CITYGML_TO_CER_CANDIDATE_MAP.jsonl
- USD_CER_SIDECAR_CANDIDATE_MAP.jsonl
- lightweight USDA handoff layer from R1
- visual mesh boundary note

## Hard boundaries
- Do not claim automatic 3D Tiles mesh object identity.
- Do not claim citywide twin readiness.
- Do not mutate prior certified outputs.
- Do not require live Omniverse or Kit if not available; produce handoff artifacts and manual review instructions.
- Treat the 3D Tiles / mesh layer as visual backdrop only unless manual alignment evidence is explicit.
- No production/legal/certified/live/autonomous claims.

## Required work

### 1. Select bounded object-pick sample
Select 20–30 CityGML/CER candidate buildings for manual alignment review.

Selection should include:
- the 20 existing smoke packets if available
- a small diversity of building IDs / spatial clusters / geometry complexity
- no more than 30 total objects

### 2. Manual alignment packet
For each selected object, create a packet with:
- alignment_packet_id
- canonical_entity_candidate_id
- CityGML gml_id
- source attributes used for review
- centroid/bbox if available
- suggested USD prim path
- suggested visual pick target / bookmark / camera note if available
- review_state
- alignment_status: pending_manual_review / aligned_by_manual_pick / rejected / ambiguous
- evidence refs
- limitation refs

### 3. Kit/Composer review checklist
Create a human review checklist for each object:
- open scene/layer
- locate visual object/backdrop position
- compare pick target against CityGML/CER identity record
- confirm or reject suggested prim path
- record reviewer initials/date if manually reviewed
- record screenshot path if available

### 4. USDA/sidecar update layer
Create a lightweight USDA or metadata sidecar layer that carries:
- manual alignment candidate markers
- canonical IDs
- source gml IDs
- evidence refs
- review_state
- alignment_status
- limitation label

If USDA writing is not feasible, emit JSON handoff with deterministic prim paths and explain limitation.

### 5. Boundary note
Explicitly separate:
- semantic CityGML identity = accepted candidate identity spine
- USD/CER sidecar = candidate handoff
- visual mesh = backdrop-only unless manually aligned
- manual object-pick R2 = small bounded review workflow, not automated alignment

## Required outputs
Create output root:
`outputs/helsinki_kit_object_pick_manual_alignment_r2/`

Required files:
- `HELSINKI_KIT_OBJECT_PICK_MANUAL_ALIGNMENT_R2_DECISION.json`
- `HELSINKI_OBJECT_PICK_ALIGNMENT_PACKETS.jsonl`
- `HELSINKI_OBJECT_PICK_ALIGNMENT_REVIEW_CHECKLIST.csv`
- `HELSINKI_OBJECT_PICK_ALIGNMENT_REVIEW_GUIDE.md`
- `HELSINKI_MANUAL_ALIGNMENT_USDA_LAYER.usda` or `HELSINKI_MANUAL_ALIGNMENT_USDA_HANDOFF.json`
- `HELSINKI_ALIGNMENT_BOUNDARY_NOTE.md`
- `HELSINKI_ALIGNMENT_SCOREBOARD.json`
- `HASH_MANIFEST.sha256`
- `RUN_AUDIT.json`

## Audits
Must run and record:
- JSON/JSONL parse audit
- sidecar field completeness audit
- no prior output mutation audit
- secret scan
- claim boundary audit
- visual mesh overclaim audit
- hash manifest verification

## Acceptance criteria
Pass with limitations if:
- at least 20 bounded manual alignment packets are produced
- every packet carries canonical/CER, CityGML, evidence, review, and limitation refs
- a Kit/Composer review guide exists
- visual mesh remains backdrop-only unless manual reviewer evidence exists
- all audits pass

Expected final status:
`PASS_HELSINKI_KIT_OBJECT_PICK_MANUAL_ALIGNMENT_R2_WITH_LIMITATIONS`
