# MAIN-CITYBRAIN-D8-NYC-CASCADE-SOURCE-EVIDENCE-MAP-R3

Create:
`outputs/main_citybrain_d8_nyc_cascade_source_evidence_map_r3`

Map every scenario claim to an existing record/path.

For each claim in `NYC_CASCADE_SCENARIO_LAYER.json`, produce:
- claim_id
- plain claim text
- claim class: source_fact / derived_review_context / uncertainty / limitation / authored_scenario_bridge
- supporting source record ids
- supporting file paths
- confidence/limits
- whether default UI may show it
- whether it must be hidden under technical details
- forbidden phrasing to avoid

Produce:
- `NYC_CASCADE_STORY_TO_SOURCE_EVIDENCE_MAP.json`
- `CLAIM_TO_SOURCE_MATRIX.csv`
- `UNSUPPORTED_CLAIM_LEDGER.json`
- `VIEWER_SAFE_COPY_REGISTER.json`
- audits/hash manifest

Any unsupported scenario claim must either be removed or downgraded to limitation/uncertainty.
