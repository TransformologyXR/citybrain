# MAIN-CITYBRAIN-D8-SOURCE-RECORD-GAP-CLOSURE-PREFLIGHT

Goal: inspect the current source-record UI freeze and confirm the exact blockers to close.

Inputs:
- `outputs/main_citybrain_d8_source_record_ui_milestone_freeze`
- `outputs/main_citybrain_d8_source_record_ui_closeout`
- `packages/fixtures/source_record_ui_integrated/`
- web source under `apps/web-control-room/`
- source-record recovery packs under `packages/fixtures/london_mobility_source_records`, `packages/fixtures/chicago_similar_case_records`, `packages/fixtures/helsinki_visual_entity_pick`

Produce:
- `SOURCE_RECORD_GAP_CLOSURE_PREFLIGHT_DECISION.json`
- `CURRENT_SOURCE_RECORD_UI_FACTS.json`
- `OPEN_SOURCE_RECORD_BLOCKER_INDEX.json`
- `SCENARIO_COHERENCE_RISK_REGISTER.json`
- `INPUT_ARTIFACT_INDEX.json`
- `HASH_MANIFEST.json`

Required assertions:
- current UI freeze status is `PASS_MAIN_CITYBRAIN_D8_SOURCE_RECORD_UI_MILESTONE_FREEZE_WITH_LIMITATIONS`.
- source-backed default cards = 27 or explain drift.
- open blockers include M13 candidate observation source detail, M07 guardrail/refusal review-log, M08 human-review stop record, unless already resolved.
- external viewer validation remains false at entry.
- no new city facts are invented.
