# MAIN-CITYBRAIN-D8-SOURCE-RECORD-BUNDLE-BUILD-R2

Build a source-record bundle for the web UI using only existing local certified/upstream data. Do not download new large datasets and do not fabricate source records.

Preferred output path:
packages/fixtures/mobility_access/source_record_bundle/

Required files:
- source_record_bundle.json
- source_record_cards.json
- source_record_to_runtime_bundle_map.json
- source_record_gaps.json
- source_attribution_ledger.json
- no_fact_invention_audit.json

Source-backed card requirements:
- Cards must show city/source/dataset/external id/place/time/summary when available.
- If a category lacks those fields, create a DATA_DEPTH_BLOCKER card, not a generic story card.
- CityBrain fixture refs can appear only as `citybrain_linkage` or technical provenance, not as the default human title.

Minimum target for green:
- At least 5 source-backed or source-derived cards OR a hard PARTIAL with a clear pivot recommendation.
- At least one visible card for each available category: place/entity, option support/evidence, similar case or observation if available.

If the current Mobility bundle is too thin, produce a pivot recommendation:
- HELSINKI_SEMANTIC_TWIN_FOR_VISUAL_ENTITY_PICK
- CHICAGO_SIMILAR_CASE_RECORD_PACK
- LONDON_MOBILITY_SOURCE_RECORD_PACK
without implementing those pilots here.
