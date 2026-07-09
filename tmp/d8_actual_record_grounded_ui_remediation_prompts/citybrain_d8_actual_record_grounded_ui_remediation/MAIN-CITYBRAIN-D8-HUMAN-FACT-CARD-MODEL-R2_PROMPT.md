# MAIN-CITYBRAIN-D8-HUMAN-FACT-CARD-MODEL-R2

## Objective

Define a UI data model that converts certified runtime bundle records into human-readable fact cards without inventing facts.

## Required model

Create a contract under `packages/contracts/human_fact_cards/`.

Minimum card types:

- `situation_fact_card`
- `entity_card`
- `relationship_link_card`
- `candidate_observation_card`
- `similar_case_card`
- `option_tradeoff_card`
- `track_d_review_stop_card`
- `uncertainty_card`
- `limitation_card`
- `trace_step_card`

Each card must include:

```json
{
  "card_id": "...",
  "card_type": "similar_case_card",
  "title": "...actual case/city/name if present...",
  "plain_summary": "...derived only from certified fields...",
  "source_record_refs": ["..."],
  "evidence_refs": ["..."],
  "confidence_or_limitation": "...",
  "technical_refs_hidden_by_default": ["..."],
  "data_depth_status": "renderable|partial|id_only|missing"
}
```

## Humanization rule

The default UI must show **what the record says**, not what CityBrain's subsystem is called.

Bad:

```text
Cross-city memory provides 4 similar cases as context.
```

Good if actual records exist:

```text
Chicago case CHI-2026-004 was matched because it also involved kerbside access disruption near a transit corridor; the prior packet was review-only and did not create a dispatch action.
```

Good if only IDs exist:

```text
4 similar-case records are present, but this bundle lacks plain-language case summaries. The records are available in technical details.
```

## Output artifacts

- `HUMAN_FACT_CARD_SCHEMA.json`
- `HUMAN_FACT_CARD_EXAMPLES.json`
- `FACT_CARD_RENDERING_RULES.md`
- `NO_FACT_INVENTION_RULES.md`
- `HASH_MANIFEST.json`

