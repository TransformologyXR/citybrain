# MAIN-CITYBRAIN-D8-NYC-FLOW3-HERO-EVIDENCE-EXTRACTION-R1

Create:
`outputs/main_citybrain_d8_nyc_flow3_hero_evidence_extraction_r1`

Goal: mine existing NYC outputs for source-backed elements needed by a concrete cascade story.

Search existing output roots only, prioritizing roots with names/contents related to:
- `f3_nyc_*`
- `affected_asset_response_context`
- `candidate_routing`
- `hero_package`
- `accepted_snapshot`
- `full_source_propagation_refresh`
- FDNY/EMS incident response
- motor vehicle collisions
- asset response context
- evidence bundles / governed briefings / trace

Extract only what is present:
- event or incident source record id(s)
- location/address/route/corridor if present
- timestamp/date/status if present
- affected asset/context records if present
- response/context records if present
- evidence refs and limitation refs
- any existing hero/story labels
- uncertainty fields or missing fields

Produce:
- `NYC_FLOW3_EVIDENCE_EXTRACTION_DECISION.json`
- `NYC_CASCADE_SOURCE_RECORD_INVENTORY.json`
- `NYC_CASCADE_EVIDENCE_CANDIDATES.json`
- `NYC_CASCADE_DATA_DEPTH_GAPS.json`
- `SOURCE_PATH_LEDGER.json`
- audits and hash manifest

If you only find high-level summaries and no concrete source records, return partial:
`PARTIAL_NYC_FLOW3_SOURCE_RECORD_DEPTH_INSUFFICIENT`.
