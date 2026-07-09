# MAIN-CITYBRAIN-D9-WATCH-NAMED-QUERY-QUEUE-R4

Implement Watch as a manual review queue from named queries.

## Not allowed

Do not implement live monitoring, alerting, push notifications, dispatch, routing/control, enforcement, or action.

## Named queries

Include:
- `watch:proximity_works_to_access@v1`
- `watch:incident_to_candidate_asset_context@v1`
- `watch:low_confidence_link_or_source_gap@v1`
- `watch:visual_identity_missing_graph_link@v1` if source inputs are adequate, otherwise partial

## Queue item requirements

- candidate id
- query id
- source refs
- review reason
- false-positive notes
- boundary statement
- recommended human review action only
- not_executed

## Required artifacts

- `D9_WATCH_NAMED_QUERY_REGISTRY.json`
- `D9_WATCH_REVIEW_QUEUE_FIXTURE.json`
- `D9_WATCH_FALSE_POSITIVE_LEDGER.json`
- `D9_WATCH_BOUNDARY_AUDIT.json`
- `D9_WATCH_NAMED_QUERY_QUEUE_R4_DECISION.json`
- audits + hash manifest

Expected status:
`PASS_MAIN_CITYBRAIN_D9_WATCH_NAMED_QUERY_QUEUE_R4_WITH_LIMITATIONS`
