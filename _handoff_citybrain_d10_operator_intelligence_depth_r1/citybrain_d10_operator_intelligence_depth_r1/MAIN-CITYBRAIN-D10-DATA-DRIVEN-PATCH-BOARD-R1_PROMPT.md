# MAIN-CITYBRAIN-D10-DATA-DRIVEN-PATCH-BOARD-R1

## Purpose

Rebuild or extend the operator patch board so the queue is generated from WATCH query outputs and ranker results, not hardcoded showcase cards.

## Product goal

The default board should remain operator-readable while being visibly data-driven: it should tell the operator what is on the patch, why it is on the patch, and what evidence supports it.

## Required actions

1. Consume `WATCH_QUERY_RUN_REPORT.json` and candidate outputs.
2. Apply admission rules:
   - `city_situation_review_item` and appropriate `source_depth_review_item` can appear in the main queue.
   - `check_only_item` appears in CHECK or inspector/status, not main queue unless tied to selected city situation.
   - `parked` never appears on the operator queue.
3. Apply deterministic `rank:city_situation@v1` or bump to `@v2` only if logic changes are documented.
4. Render queue cards in operator language only:
   - Why this needs review
   - Why this is ranked here
   - Records on file
   - What may be nothing
   - Suggested human check
5. Preserve `data-mode-run-id` and source traceability in DOM/inspector.
6. Keep technical IDs/paths/templates invisible in default operator text.

## Output

Write:

`outputs/main_citybrain_d10_data_driven_patch_board_r1/DATA_DRIVEN_PATCH_BOARD_REPORT.json`

Minimum schema:

```json
{
  "task": "MAIN-CITYBRAIN-D10-DATA-DRIVEN-PATCH-BOARD-R1",
  "status": "PASS_DATA_DRIVEN_PATCH_BOARD_WITH_LIMITATIONS",
  "source_watch_report": "...",
  "queue_items_rendered": 0,
  "admitted_from_query_outputs": 0,
  "hardcoded_showcase_items_removed_or_justified": true,
  "ranker_version": "rank:city_situation@v1",
  "excluded_candidates": [],
  "operator_visible_forbidden_terms_zero": true,
  "limitations": []
}
```

## Acceptance

- Queue is derived from query outputs or explicitly documented if data does not support expansion.
- Queue has city situation titles and source-backed reasons.
- Existing D9 Wood Lane/NYC items may remain only as query outputs, not as hand-pinned demos.

## Fail if

- The board simply re-labels the same hardcoded cards without query-run lineage.
- Operator text regresses into platform terms.
- Rank implies authority, urgency, or action.
