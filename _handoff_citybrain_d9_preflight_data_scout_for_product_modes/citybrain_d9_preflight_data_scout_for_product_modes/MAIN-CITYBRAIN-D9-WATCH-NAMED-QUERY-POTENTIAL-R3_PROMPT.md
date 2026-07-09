# MAIN-CITYBRAIN-D9-WATCH-NAMED-QUERY-POTENTIAL-R3

Create output root:
`outputs/main_citybrain_d9_watch_named_query_potential_r3`

Scout named WATCH queries. Do not implement the queue; identify what named queries can produce useful review candidates from existing data.

Candidate query families:
- `story-query:proximity_works_to_access@v1` — London works near access asset; already has Wood Lane plus duplicate-shape candidates.
- `story-query:incident_to_affected_asset_response_cascade@v1` — NYC incident/candidate affected asset/response context.
- `story-query:source_depth_blocker@v1` — missing media observation/source details, missing refusal log, missing viewer records.
- `story-query:duplicate_shape_cluster@v1` — London same-shape candidates not counted as distinct stories.
- `story-query:visual_entity_pick_resolution@v1` — Helsinki source building to prim/entity mapping as capability cutaway.

For each query, report:
- query_id@version
- inputs
- candidate count
- ranked examples
- product role: primary story / trust moment / cutaway / blocker
- can it run deterministically now?
- risk of false implication

Produce:
- WATCH_NAMED_QUERY_CANDIDATE_REGISTRY.json
- WATCH_QUEUE_ITEM_PROTOTYPES.json
- WATCH_QUERY_DUPLICATE_SHAPE_AUDIT.json
- WATCH_QUERY_RISK_LEDGER.json
- WATCH_SCOUT_DECISION.json

Acceptance:
- PASS if at least 3 named query families are useful without overclaim.
- PARTIAL if only story queries are usable but CHECK/DIFF blockers are useful.
