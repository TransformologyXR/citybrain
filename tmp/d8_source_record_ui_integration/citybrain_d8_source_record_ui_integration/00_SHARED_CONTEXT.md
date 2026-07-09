# CityBrain D8 — Source-Record UI Integration

Purpose: make the live web control-room consume the newly recovered London, Chicago, and Helsinki source-record bundles so the default UI shows real/source-derived city facts, not CityBrain fixture labels.

## Current validated upstream

`PASS_MAIN_CITYBRAIN_D8_SOURCE_RECORD_RECOVERY_CERTIFIED_STATE_HANDOFF_WITH_LIMITATIONS`

Validated facts:
- London Mobility source records: 10 source records / 10 UI-ready cards.
- Chicago Similar Case records: 5 source-backed similar cases / 5 UI-ready cards.
- Helsinki Visual Entity Pick records: 12 semantic building records / 12 prim-mapped cards.
- External viewer validation remains false until the web UI consumes these bundles.
- M13 candidate observation, M07 refusal log, and M08 external review-stop records remain blocked/runtime-only unless source records exist.

## Non-negotiable product rule

Default UI cards must be backed by official or source-derived city records.

Allowed in default UI:
- OFFICIAL_CITY_SOURCE_RECORD
- SOURCE_DERIVED_CITY_RECORD
- DATA_DEPTH_BLOCKER

Not allowed in default UI:
- CITYBRAIN_FIXTURE_RECORD
- INTERNAL_OPTION_PACKET
- TRACE_STAGE_LABEL
- GENERATED_HERO_LABEL
- raw IDs such as `HERO-LON-CORRIDOR...`, `similar_case:001`, `d7_candidate_observation:001`, `inv_option_*`, `track-d-*`

Those may appear only inside collapsed technical details.

## Source bundle roots expected

- `packages/fixtures/london_mobility_source_records/source_record_bundle.json`
- `packages/fixtures/chicago_similar_case_records/similar_case_source_bundle.json`
- `packages/fixtures/helsinki_visual_entity_pick/source_record_bundle.json`
- `packages/fixtures/source_record_recovery_candidate_bundle/source_record_recovery_candidate_bundle.json`

If a bundle is missing, return PARTIAL with a specific data/source gap. Do not synthesize city facts.

## Boundary

This is still local/LAN/replay/review/query context only. No production/public API, live monitoring, autonomous action, dispatch, routing/control, enforcement, ticket/case creation, legal/certified finding, or approval claim.
