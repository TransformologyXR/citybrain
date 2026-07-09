# MAIN-CITYBRAIN-D8-INTEGRATED-SOURCE-RECORD-BUNDLE-ADAPTER-R1

## Goal
Create a single adapter output that the web UI can read without inventing facts.

## Scope
Read:
- London mobility source bundle.
- Chicago similar-case bundle.
- Helsinki visual entity pick bundle.
- source record recovery candidate bundle.

Write:
- `packages/fixtures/source_record_ui_integrated/source_record_ui_integrated_bundle.json`
- `packages/fixtures/source_record_ui_integrated/source_record_ui_card_index.json`
- `packages/fixtures/source_record_ui_integrated/source_record_ui_data_depth_blockers.json`

## Required card types
Each default card must have:
- `card_id`
- `card_type`
- `record_class`: one of `OFFICIAL_CITY_SOURCE_RECORD`, `SOURCE_DERIVED_CITY_RECORD`, `DATA_DEPTH_BLOCKER`
- `source_city`
- `source_system_or_dataset`
- `title`
- `plain_language_summary`
- `city_fact_fields`
- `evidence_refs`
- `limitations`
- `not_a_finding` boolean when applicable
- `technical_refs` for raw IDs, rendered only in technical details.

## Required sections
- `situation_city_records`: London mobility records.
- `similar_case_city_records`: Chicago source-backed cases.
- `visual_entity_city_records`: Helsinki semantic building/prim records.
- `data_depth_blockers`: M13, M07, M08 if still source-thin.
- `technical_refs`: raw CityBrain IDs kept separate.

## Forbidden
Do not create a source card from:
- `HERO-LON-CORRIDOR...`
- `mobility_access:*`
- `similar_case:001` without source-backed case details
- `d7_candidate_observation:*` without source/time/location/label/summary
- `inv_option_*`
- `track-d-*`
- trace stage labels alone.

## Outputs
Create `outputs/main_citybrain_d8_integrated_source_record_bundle_adapter_r1` with:
- `INTEGRATED_SOURCE_RECORD_BUNDLE_ADAPTER_DECISION.json`
- `SOURCE_RECORD_UI_INTEGRATED_BUNDLE_SUMMARY.json`
- `FIXTURE_REF_QUARANTINE_LEDGER.json`
- `DATA_DEPTH_BLOCKERS_FOR_UI.json`
- audits and hash manifest.

## Status rules
PASS if an integrated bundle exists with >0 eligible source-backed cards and all fixture-only refs are quarantined.
PARTIAL if source records exist but no current web panel can consume them yet.
FAIL if fixture IDs are promoted as source records.
