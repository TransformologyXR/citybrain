# MAIN-CITYBRAIN-D10-RECALL-FIELD-MATCH-REASONS-R1

## Purpose

Turn RECALL from generic precedent cards into field-computed similar-record memory where current data supports it.

## Product goal

When an operator asks "have we seen something like this before?", CityBrain should show prior records and the exact fields that made them similar.

## Required actions

1. Inventory available recall-capable datasets, especially Chicago violation/inspection/case records and any analogous local records.
2. Define deterministic similarity features available from fields, such as:
   - issue type/category
   - ward/community area/neighbourhood/city district
   - address block/street if available
   - source/domain
   - time window/as-of proximity
   - asset/type/context overlap
3. Build or contract `recall:field_match@v1`.
4. For each matched record, output:
   - matched record label
   - source record ID
   - matched fields and values
   - non-matching/unknown fields
   - match strength from field overlap
   - cannot-claim: no causality, no outcome prediction, no recommendation, no enforcement
5. Include designed non-match tests.
6. If recall cannot be meaningfully computed for a selected item, keep it out of default view and show an honest unavailable state.

## Output

Write:

`outputs/main_citybrain_d10_recall_field_match_reasons_r1/RECALL_FIELD_MATCH_REASON_REPORT.json`

Minimum schema:

```json
{
  "task": "MAIN-CITYBRAIN-D10-RECALL-FIELD-MATCH-REASONS-R1",
  "status": "PASS_RECALL_FIELD_MATCH_REASONS_WITH_LIMITATIONS" ,
  "recall_index_sources": [],
  "feature_schema": [],
  "matches_computed": 0,
  "matches_with_field_reasons": 0,
  "generic_match_reasons_remaining": 0,
  "designed_non_matches_passed": 0,
  "default_surface_policy": "show_when_field_reasons_available_else_drawer_or_unavailable",
  "limitations": []
}
```

## Acceptance

- No generic "similar case" reasons in operator-visible default view.
- At least one positive match with field reasons if data supports it, or an honest no-ready-recall result.
- Designed non-match does not match.

## Fail if

- Recall implies causality or prediction.
- Recall match reasons are generic prose not computed from fields.
- Recall appears in default view despite generic/weak reasons.
