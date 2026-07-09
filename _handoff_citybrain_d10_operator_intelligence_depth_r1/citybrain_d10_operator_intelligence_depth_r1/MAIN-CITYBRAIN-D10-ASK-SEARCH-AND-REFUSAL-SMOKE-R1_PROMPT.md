# MAIN-CITYBRAIN-D10-ASK-SEARCH-AND-REFUSAL-SMOKE-R1

## Purpose

Smoke-test deterministic city-data search and ASK behavior after D10 product-depth changes.

## Product goal

Operators should be able to ask supported questions about selected items and records, get cited answers, and see clean refusals for unsupported questions.

## Required smoke set

Create and run a smoke set with at least 12 tests:

### Supported answers
- selected item: what do we know?
- selected item: what records support this?
- selected item: what is uncertain?
- selected item: what can we not claim?
- entity/non-story asset brief subject lookup
- source-depth gap query
- city/domain/time record filter where supported
- recall field-match query where supported

### Refusals
- action-shaped request: "dispatch / notify / close / route / enforce"
- legal/finding request: "is this illegal / certify affected building"
- prediction request: "will this cause disruption"
- unsupported entity outside local source graph

## Output

Write:

`outputs/main_citybrain_d10_ask_search_and_refusal_smoke_r1/ASK_SEARCH_AND_REFUSAL_SMOKE_REPORT.json`

Minimum schema:

```json
{
  "task": "MAIN-CITYBRAIN-D10-ASK-SEARCH-AND-REFUSAL-SMOKE-R1",
  "status": "PASS_ASK_SEARCH_AND_REFUSAL_SMOKE_WITH_LIMITATIONS",
  "tests_total": 0,
  "supported_answer_tests": 0,
  "supported_answer_pass": 0,
  "refusal_tests": 0,
  "refusal_pass": 0,
  "answers_with_citations": 0,
  "unsupported_citations_count": 0,
  "model_router_used": false,
  "failures": [],
  "limitations": []
}
```

## Acceptance

- Supported answers cite records.
- Unsupported/action/legal/prediction requests refuse.
- No model/Open ASK router is used.
- No unsupported sources are introduced.

## Fail if

- Action-shaped requests become review options or instructions.
- Unsupported questions return generic prose as an answer.
- Any answer includes claims without cited retained records or certified runtime fields.
