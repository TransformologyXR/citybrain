# MAIN-CITYBRAIN-D8-LONDON-MOBILITY-UI-RECORD-BUNDLE-R3

Goal: create a UI-ready source record bundle that can replace fixture labels in the web control room.

Outputs:
- packages/fixtures/london_mobility_source_records/source_record_bundle.json
- packages/fixtures/london_mobility_source_records/human_fact_cards.json
- packages/fixtures/london_mobility_source_records/ui_panel_mapping.json
- LONDON_MOBILITY_UI_RECORD_ASSERTION_PLAN.json

Required mappings:
- Situation panel uses actual London source records, not `Hero Lon Corridor`.
- Evidence panel uses actual records or explicit data-depth blockers.
- Options panel may reference Mobility Access option packets only if paired with source facts.
- Technical IDs remain collapsed.

PASS if at least 5 viewer-readable source-backed cards are produced.
PARTIAL if fewer than 5.
