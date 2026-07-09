# MAIN-CITYBRAIN-D10-DETERMINISTIC-CITY-DATA-SEARCH-CONTRACT-R1

## Purpose

Define and implement a deterministic city-data search/template contract for the cockpit. This is not Open ASK router implementation. It is a closed set of supported searches over retained records.

## Product goal

When an operator asks or clicks a suggested question, CityBrain should search retained city data and answer with citations, or refuse with a missing-evidence reason.

## Required search behaviors

Implement or contract supported deterministic search templates such as:

1. `search:entity_records@v1` — find records mentioning a selected entity/asset/address ID.
2. `search:source_records_for_item@v1` — list the records supporting a selected queue item.
3. `search:uncertainty_for_item@v1` — list unknowns/missing evidence/cannot-claim for a selected item.
4. `search:nearby_context@v1` — bounded nearby/candidate context where a spatial or source link exists.
5. `search:brief_subject_candidates@v1` — identify non-story subjects that can support a brief.
6. `search:source_depth_gaps@v1` — find items where a desired claim lacks direct support.
7. `search:records_by_city_domain_time@v1` — filter retained records by city/domain/time where fields exist.
8. `search:similar_records_by_fields@v1` — supports RECALL, deterministic field overlap only.

The UI may expose these as suggested questions or chips. No free-form model answering.

## Router limit

Allowed: deterministic lexical mapping from suggested chips or exact supported phrases to templates.

Forbidden here:

- LLM router
- open free-form natural language answering
- answer text generated without assembled evidence
- unsupported nearest-question suggestions that imply coverage not present

## Output

Write:

`outputs/main_citybrain_d10_deterministic_city_data_search_contract_r1/CITY_DATA_SEARCH_TEMPLATE_LIBRARY.json`

Minimum schema:

```json
{
  "task": "MAIN-CITYBRAIN-D10-DETERMINISTIC-CITY-DATA-SEARCH-CONTRACT-R1",
  "status": "PASS_CITY_DATA_SEARCH_CONTRACT_WITH_LIMITATIONS",
  "open_ask_router_implemented": false,
  "templates": [
    {
      "template_id": "search:...@v1",
      "operator_label": "...",
      "supported_questions": [],
      "args_schema": {},
      "retrieval_logic": "deterministic description",
      "answer_sections": ["summary", "records_on_file", "knowns", "unknowns", "cannot_claim", "citations"],
      "refusal_conditions": [],
      "golden_cases": [],
      "designed_non_matches": []
    }
  ],
  "refusal_contract": {
    "requires_reason": true,
    "requires_zero_unsupported_citations": true,
    "nearest_supported_questions_allowed": true
  }
}
```

## Acceptance

- At least 6 templates defined or implemented with golden/non-match cases.
- Every template cites retained records or returns a refusal.
- No Open ASK/model router is added.

## Fail if

- A model writes factual answers.
- Unsupported questions silently fall back to generic prose.
- The cockpit presents search as complete-city coverage.
