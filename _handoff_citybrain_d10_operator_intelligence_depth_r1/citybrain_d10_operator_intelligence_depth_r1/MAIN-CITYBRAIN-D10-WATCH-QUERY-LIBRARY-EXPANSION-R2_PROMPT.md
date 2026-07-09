# MAIN-CITYBRAIN-D10-WATCH-QUERY-LIBRARY-EXPANSION-R2

## Purpose

Expand WATCH from a few showcase/manual review cards into a named query library that can generate data-driven review candidates over retained local source records.

## Product goal

WATCH should answer: "What deserves human eyes in this replay window, and why?"

## Required query classes

Build or contract named deterministic query classes where source fields support them:

1. `watch:works_near_access_asset@v2`
2. `watch:incident_near_candidate_asset_context@v2`
3. `watch:source_depth_gap@v1`
4. `watch:stale_or_missing_time_record@v1`
5. `watch:low_confidence_identity_or_geometry_link@v1`
6. `watch:evidence_rich_non_story_entity@v1`
7. `watch:recall_candidate_available@v1`
8. `watch:diff_snapshot_prerequisite_gap@v1` (CHECK/status item, not main queue unless tied to a city situation)

If a query cannot run due missing fields, park it with a reason. Do not fake it.

## Required fields per emitted candidate

Each candidate must include:

- city
- operator title
- place/entity label
- as-of/record time
- source records with city-source-first labels
- why this needs review
- why ranked here
- what may be nothing
- suggested human check
- admission class: `city_situation_review_item`, `source_depth_review_item`, `check_only_item`, or `parked`
- no-action boundary

## Output

Write:

1. `outputs/main_citybrain_d10_watch_query_library_expansion_r2/WATCH_QUERY_LIBRARY_R2.json`
2. `outputs/main_citybrain_d10_watch_query_library_expansion_r2/WATCH_QUERY_RUN_REPORT.json`

Minimum report fields:

```json
{
  "task": "MAIN-CITYBRAIN-D10-WATCH-QUERY-LIBRARY-EXPANSION-R2",
  "status": "PASS_WATCH_QUERY_LIBRARY_EXPANSION_WITH_LIMITATIONS",
  "queries_defined": 0,
  "queries_runnable": 0,
  "queries_parked": 0,
  "candidate_counts_by_class": {},
  "candidate_counts_by_city": {},
  "golden_cases_passed": 0,
  "designed_non_matches_passed": 0,
  "operator_queue_candidates": [],
  "check_only_candidates": [],
  "parked_queries": []
}
```

## Acceptance

- At least 6 query classes defined.
- At least 3 runnable over current retained local data, if available.
- At least one non-Wood-Lane candidate or honest limitation explaining why not.
- Every emitted candidate has sources and operator-readable reason text.

## Fail if

- WATCH implies live monitoring, alerting, notification, dispatch, or urgency-as-finding.
- Query output is fixture-order cards with post-hoc rationale.
- Query output uses internal IDs as the operator title.
