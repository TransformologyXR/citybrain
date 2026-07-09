# MAIN-CITYBRAIN-D9-MODE-SURFACE-INPUT-INVENTORY-R1

Create output root:
`outputs/main_citybrain_d9_mode_surface_input_inventory_r1`

Inventory all source inputs that D9 modes might surface. Classify each artifact as:
- OFFICIAL_SOURCE_RECORD
- SOURCE_DERIVED_RECORD
- AUTHORED_SCENARIO_LAYER
- GOVERNED_TRACE_RECORD
- OPTION_SET_RECORD
- HUMAN_REVIEW_BOUNDARY_RECORD
- TRUST_MOMENT_RECORD
- CAPABILITY_CUTAWAY_RECORD
- DATA_DEPTH_BLOCKER
- INTERNAL_FIXTURE_ONLY

Group by mode suitability:
- ASK: can answer direct questions with citations.
- WATCH: can generate named review query queue items.
- RECALL: can serve as precedent/similar-case memory.
- BRIEF: can be assembled into an evidence packet.
- CHECK: can reveal conflict, missing fields, thin evidence, low confidence, duplicate query shapes.
- DIFF: can support change-over-time.

Produce:
- MODE_SURFACE_INPUT_INVENTORY.json
- MODE_SURFACE_INPUT_SUMMARY.md
- INTERNAL_FIXTURE_NOT_PRODUCT_VALUE_LEDGER.json
- DATA_DEPTH_BLOCKERS_BY_MODE.json
- MODE_SURFACE_INPUT_INVENTORY_DECISION.json

Acceptance:
- PASS if every input used by D9 is classified and modes have a candidate input set.
- PARTIAL if some modes have no adequate input and blockers are explicit.
