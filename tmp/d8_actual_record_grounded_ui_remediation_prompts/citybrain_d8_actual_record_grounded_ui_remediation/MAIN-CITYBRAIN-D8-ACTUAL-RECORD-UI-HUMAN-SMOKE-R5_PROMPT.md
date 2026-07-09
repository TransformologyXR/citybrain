# MAIN-CITYBRAIN-D8-ACTUAL-RECORD-UI-HUMAN-SMOKE-R5

## Objective

Run a local non-external smoke test over the patched UI to determine whether it now explains the actual city records/cases/observations/options, not just CityBrain mechanics.

## Smoke criteria

A reviewer should be able to answer from the default UI:

1. What is the actual scenario/corridor/place?
2. Which actual records/entities are involved?
3. What observations exist, and what do they say?
4. Which similar cases exist, and why were they matched?
5. Which link is uncertain and why?
6. Which review options exist and how do they compare?
7. Why does the system stop at human review?
8. What data is missing or still too shallow?

If the UI cannot answer a question because the bundle lacks data, the UI must say that explicitly.

## Output artifacts

- `ACTUAL_RECORD_UI_HUMAN_SMOKE_REPORT.json`
- `VIEWER_READY_GAP_LEDGER.json`
- `DEFAULT_UI_QUESTION_ANSWER_MATRIX.md`
- `HASH_MANIFEST.json`

