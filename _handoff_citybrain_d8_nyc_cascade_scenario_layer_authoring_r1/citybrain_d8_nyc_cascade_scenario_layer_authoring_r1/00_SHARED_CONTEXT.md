# CityBrain D8 — NYC Cascade Scenario Layer Authoring R1

Purpose: convert the `authoring_plan_only` NYC cascade candidate from the D8 scenario-authoring run into a concrete, source-backed scenario layer if and only if existing Flow 3 / NYC outputs contain enough evidence.

This is not a UI redesign and not a new-data landing sprint. It is scenario-layer authoring over existing certified outputs.

Durable boundary:
- local/replay/review/query context only
- no production/public API claim
- no autonomous monitoring/alerts
- no dispatch, routing/control, enforcement, official ticket/case, legal/certified finding, or automated action
- no impact/causality claim unless the source records explicitly prove it
- Track D/human review remains authoritative
- execution_state remains not_executed

Target story-query:
`story-query:incident_to_affected_asset_response_cascade@v1`

Baseline from previous run:
- D8 Scenario Authoring R1 found 2 distinct story-query versions:
  - `story-query:proximity_works_to_access@v1`
  - `story-query:incident_to_affected_asset_response_cascade@v1`
- Wood Lane remains the authored baseline proximity/access story.
- NYC MVC cascade is currently `authoring_plan_only`; this pack tries to turn it into a concrete scenario layer.
- London Warwick/Lancaster/Claps Gate are duplicate-shape proximity stories and should not be counted as distinct primaries.
- Chicago/Helsinki remain cutaways/trust/capability moments unless paired to a standalone tension.

Pass with limitations is acceptable. If evidence is too thin, return:
`PARTIAL_NYC_CASCADE_SCENARIO_EVIDENCE_INSUFFICIENT`
