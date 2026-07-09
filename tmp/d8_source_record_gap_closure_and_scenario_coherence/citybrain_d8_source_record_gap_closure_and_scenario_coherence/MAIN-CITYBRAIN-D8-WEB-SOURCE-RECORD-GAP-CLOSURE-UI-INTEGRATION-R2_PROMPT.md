# MAIN-CITYBRAIN-D8-WEB-SOURCE-RECORD-GAP-CLOSURE-UI-INTEGRATION-R2

Goal: update the web control room to consume the new M13/M07/M08 record packs where available and to reflect the London coherence verdict honestly.

Inputs:
- D7 media observation record pack.
- guardrail refusal review-log pack.
- human-review stop record pack.
- London coherence verdict.
- existing source-record UI integrated bundle.

Patch only:
- `packages/fixtures/source_record_ui_integrated/` derived integration bundle(s).
- `apps/web-control-room/` rendering code and templates as needed.

Default UI rules:
- show source-backed city/source records where present.
- show explicit data-depth blockers where records remain missing.
- if London records are source examples, do not call them a single corridor incident.
- no fixture IDs in default UI.
- no generic "CityBrain connected X" without showing record cards or blockers.

Produce:
- `WEB_SOURCE_RECORD_GAP_CLOSURE_UI_INTEGRATION_R2_DECISION.json`
- `UPDATED_SOURCE_RECORD_UI_TRUTH_REGISTER.json`
- `WEB_CITY_FACT_DOM_ASSERTION_REPORT.json`
- `NO_GENERIC_FIXTURE_LABEL_AUDIT.json`
- `HASH_MANIFEST.json`
