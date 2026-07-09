# MAIN-CITYBRAIN-D10-SOURCE-AND-QUERY-CANDIDATE-INVENTORY-R1

## Purpose

Inventory retained local city sources and identify useful deterministic query candidates. This is the foundation for a data-driven cockpit. Do not hardcode a fixed three-card board as the product.

## Product question

What useful city-operator questions can be answered or queued from the data already on file?

## Required actions

1. Walk retained local fixtures and relevant outputs for source-record bundles and runtime bundles.
2. Classify sources by city, domain, record type, timestamp availability, entity IDs, location fields, and citation quality.
3. Identify query candidates by domain and source shape, for example:
   - works near access asset
   - incident near candidate asset/context record
   - source-depth gap
   - stale record or missing timestamp
   - low-confidence link
   - cross-source disagreement where comparable fields exist
   - entity records mentioning the same address/asset/corridor
   - evidence-rich non-story entity brief candidate
   - recall candidate based on shared issue type/location/time fields
4. For each candidate, decide whether it is usable now, partial, or parked.
5. Keep internal/system/cutaway items out of the operator queue unless tied to a city situation.

## Output

Write:

`outputs/main_citybrain_d10_source_and_query_candidate_inventory_r1/SOURCE_AND_QUERY_CANDIDATE_REGISTRY.json`

Minimum schema:

```json
{
  "task": "MAIN-CITYBRAIN-D10-SOURCE-AND-QUERY-CANDIDATE-INVENTORY-R1",
  "status": "PASS_SOURCE_QUERY_CANDIDATE_INVENTORY_WITH_LIMITATIONS",
  "source_inventory": [
    {
      "source_id": "...",
      "city": "London|NYC|Chicago|Helsinki|Barcelona|Singapore|Cross-city",
      "domain": "mobility|planning|incident|asset|visual|inspection|complaint|other",
      "record_count": 0,
      "timestamp_fields": [],
      "entity_fields": [],
      "location_fields": [],
      "citation_quality": "strong|partial|weak",
      "operator_usefulness": "strong|partial|weak|parked",
      "limitations": []
    }
  ],
  "query_candidates": [
    {
      "candidate_id": "query-candidate:...",
      "operator_question": "...",
      "candidate_query_type": "...",
      "input_sources": [],
      "expected_output": "queue_item|ask_answer|brief_subject|check_finding|recall_match|diff_status",
      "readiness": "ready|partial|parked",
      "missing_prerequisites": [],
      "no_action_boundary": true
    }
  ],
  "blocked_or_parked": []
}
```

## Acceptance

- At least 10 query candidates should be registered if source inventory supports them.
- At least 4 should be ready or partial product candidates beyond the original Wood Lane card.
- Every candidate must have source-backed input sources or be parked.

## Fail if

- Query candidates are invented without source backing.
- The registry treats stories as the only source of product value.
- Internal/cutaway engineering items are admitted as operator city situations.
