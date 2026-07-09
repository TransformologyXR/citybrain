# MAIN-CITYBRAIN-D8-RUNTIME-BUNDLE-DATA-DEPTH-AUDIT-R1

## Objective

Inspect the certified Mobility Access runtime bundle and determine what actual human-meaningful data exists for rendering. Do not patch the UI yet.

## Required audit tables

Create `RUNTIME_BUNDLE_DATA_DEPTH_AUDIT.json` and `RUNTIME_BUNDLE_DATA_DEPTH_AUDIT.md` covering these categories:

1. Scenario/place/corridor facts
2. Mobility Access entity refs
3. Relationship families and actual links
4. D7 candidate observations
5. Similar cases
6. Cascade/context links
7. Option sets and candidate options
8. Shared-axis tradeoff values
9. Track D promotion/non-promotion packets
10. Limitations and uncertainty/confidence fields
11. Trace stages with concrete inputs/outputs

For each category, record:

```json
{
  "category": "similar_cases",
  "record_count": 4,
  "actual_record_fields_found": ["case_id", "city", "domain", "match_reason", "evidence_refs"],
  "human_readable_fields_found": ["city", "case_summary"],
  "missing_human_fields": ["plain_language_outcome"],
  "can_render_default_ui": true,
  "requires_data_depth_gap": false
}
```

## Strict failure/partial logic

- If only IDs/counts exist, the category is not demo-ready.
- If a category lacks actual record payloads, create a `DATA_DEPTH_GAP` row.
- Do not backfill content unless it is derived directly from certified fields.
- Do not invent street names, case summaries, observations, asset names, confidence values, or outcomes.

## Output artifacts

- `RUNTIME_BUNDLE_DATA_DEPTH_AUDIT.json`
- `RUNTIME_BUNDLE_DATA_DEPTH_AUDIT.md`
- `DATA_DEPTH_GAP_LEDGER.json`
- `RENDERABLE_RECORD_INVENTORY.json`
- `NON_RENDERABLE_GENERIC_LABELS_TO_REMOVE.json`
- `HASH_MANIFEST.json`

