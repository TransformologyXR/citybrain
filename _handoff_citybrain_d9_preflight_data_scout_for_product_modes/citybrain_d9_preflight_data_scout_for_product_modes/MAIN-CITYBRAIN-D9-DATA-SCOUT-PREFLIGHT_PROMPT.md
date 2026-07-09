# MAIN-CITYBRAIN-D9-DATA-SCOUT-PREFLIGHT

Create output root:
`outputs/main_citybrain_d9_data_scout_preflight`

Inputs to locate:
- `packages/fixtures/brain_surface_story_queue/brain_surface_story_queue_bundle.json`
- `packages/fixtures/story_first_demo/story_scenario_layer.json`
- `packages/fixtures/nyc_cascade_story_scenario_layer/NYC_CASCADE_SCENARIO_LAYER.json`
- `packages/fixtures/source_record_ui_integrated/source_record_ui_integrated_bundle.json`
- `packages/fixtures/london_mobility_source_records/source_record_bundle.json`
- `packages/fixtures/chicago_similar_case_records/similar_case_source_bundle.json`
- `packages/fixtures/helsinki_visual_entity_pick/source_record_bundle.json`
- latest D8 story queue, source-record recovery, and scenario authoring output roots.

Produce:
- PREFLIGHT_INPUT_INDEX.json
- D8_CURRENT_STORY_QUEUE_BASELINE.json
- D9_SCOUT_SCOPE_LOCK.json
- CLAIM_BOUNDARY_AUDIT.json
- NO_MUTATION_AUDIT.json
- SECRET_AUDIT.json
- HASH_MANIFEST.json
- DATA_SCOUT_PREFLIGHT_DECISION.json

Acceptance:
- PASS if two-story queue baseline is found and no mutation needed.
- PARTIAL if only one story baseline is found but enough data exists to scout ASK/BRIEF.
- FAIL if baseline files cannot be located.
