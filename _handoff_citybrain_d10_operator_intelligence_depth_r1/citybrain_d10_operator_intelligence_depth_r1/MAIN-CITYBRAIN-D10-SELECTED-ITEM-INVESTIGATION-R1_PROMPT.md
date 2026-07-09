# MAIN-CITYBRAIN-D10-SELECTED-ITEM-INVESTIGATION-R1

## Purpose

Make the selected-item view function like an investigation workspace, not just a summary card.

## Product goal

When an operator selects a queue item, the board should answer:

- Why is this item here?
- What records are on file?
- What is known?
- What is missing?
- What may be nothing?
- What can I ask next?
- What brief can I generate?
- What checks constrain this item?

## Required actions

1. For each admitted queue item, build a selected-item investigation object.
2. Include sections:
   - situation summary
   - records on file with city-source-first labels and times
   - why this needs review
   - source chain/provenance pointer
   - knowns
   - unknowns/missing evidence
   - what this does not prove
   - suggested deterministic questions/searches
   - available brief subjects
   - check findings
   - optional recall availability
3. Ensure selected context is explicit for all ASK/BRIEF/CHECK actions. No ambiguous `packet=current` in visible text.
4. Keep inspector details available but collapsed.

## Output

Write:

`outputs/main_citybrain_d10_selected_item_investigation_r1/SELECTED_ITEM_INVESTIGATION_REPORT.json`

Minimum schema:

```json
{
  "task": "MAIN-CITYBRAIN-D10-SELECTED-ITEM-INVESTIGATION-R1",
  "status": "PASS_SELECTED_ITEM_INVESTIGATION_WITH_LIMITATIONS",
  "items_with_investigation_objects": 0,
  "items_missing_source_records": [],
  "items_missing_timestamps": [],
  "suggested_question_count": 0,
  "brief_subject_count": 0,
  "check_findings_attached": 0,
  "limitations": []
}
```

## Acceptance

- Every visible queue item has an investigation object.
- Every investigation object has records, unknowns, cannot-claim, and suggested next questions/checks.
- No visible technical IDs are needed to understand the item.

## Fail if

- The selected view is merely a duplicate of the queue card.
- Suggested questions are unsupported by deterministic templates.
- Any action/recommendation language appears.
