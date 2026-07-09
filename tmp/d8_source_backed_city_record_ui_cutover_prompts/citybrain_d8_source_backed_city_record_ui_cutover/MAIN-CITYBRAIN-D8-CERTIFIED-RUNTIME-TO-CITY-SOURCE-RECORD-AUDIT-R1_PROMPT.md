# MAIN-CITYBRAIN-D8-CERTIFIED-RUNTIME-TO-CITY-SOURCE-RECORD-AUDIT-R1

Audit the certified runtime bundle and adjacent upstream outputs for real city-source depth.

For every candidate record, classify:
- OFFICIAL_CITY_SOURCE_RECORD: external city dataset row/feature with source dataset and external id.
- SOURCE_DERIVED_CITY_RECORD: derived from official source with traceable source refs.
- CITYBRAIN_FIXTURE_RECORD: internally generated scenario/option/trace/entity ref only.
- DATA_DEPTH_BLOCKER: refs/counts exist but no viewer-readable source fields.

Required output files:
- CITY_SOURCE_RECORD_AUDIT.json
- CITY_SOURCE_RECORD_INVENTORY.json
- CITYBRAIN_FIXTURE_RECORD_LEDGER.json
- DATA_DEPTH_BLOCKERS_FOR_UI.json
- SOURCE_RECORD_MINIMUM_FIELD_SCHEMA.json

Minimum source-record fields:
- display_title
- source_system / dataset_name
- external_record_id or official/source-derived identifier
- city
- place/address/road/building/camera/location label if available
- timestamp/date if available
- geometry/location ref if available
- relevant source fields excerpt
- source_path_or_url / local source file path
- license/attribution if known
- citybrain_entity_link
- limitation_label

Fail-safe: if the Mobility Access bundle has no OFFICIAL_CITY_SOURCE_RECORD or SOURCE_DERIVED_CITY_RECORD cards, output PARTIAL_SOURCE_RECORD_DEPTH_INSUFFICIENT and recommend the nearest data-backed pivot (e.g. Helsinki semantic twin, Chicago similar-case packets, London/TfL mobility records) instead of fabricating cards.
