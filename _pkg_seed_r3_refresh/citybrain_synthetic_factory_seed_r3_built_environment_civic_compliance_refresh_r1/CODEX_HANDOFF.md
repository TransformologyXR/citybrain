# Codex Handoff — MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-BUILT-ENVIRONMENT-CIVIC-COMPLIANCE-REFRESH-R1

## Objective

Use the locked Seed R3 cross-city domain fuel preflight to generate a bounded non-mobility Seed R3 refresh for CityBrain's synthetic factory.

Seed R2 made the product loop alive through mobility. Seed R3 should extend the loop into:

1. property / planning
2. built environment
3. building compliance
4. civic service / 311 / CRM
5. environment / resilience
6. data quality / maturity
7. identity / graph evaluation

## Required inputs

```text
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-CROSS-CITY-DOMAIN-FUEL-PREFLIGHT
```

Optional read-only context:

```text
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R1
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R2-MOBILITY-DEPTH-REFRESH
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-SERVED-RUNTIME-INTEGRATION-R1
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D6-SERVED-CONTROL-ROOM-INTEGRATION-R1
```

## Required output root

```text
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-BUILT-ENVIRONMENT-CIVIC-COMPLIANCE-REFRESH-R1
```

## Required result files

- `SEED_R3_BEE_CIVIC_COMPLIANCE_DECISION.json`
- `SEED_R3_DOMAIN_SELECTION_LEDGER.csv`
- `SEED_R3_SYNTHETIC_ENTITY_REFRESH.jsonl`
- `EVENT_REPLAY_SEED_R3.jsonl`
- `WATCH_SEED_R3.jsonl`
- `ASK_SEED_R3.jsonl`
- `CHECK_SEED_R3.jsonl`
- `BRIEF_SEED_R3.jsonl`
- `SPATIAL_SEED_R3.jsonl`
- `QUALITY_MATURITY_FIXTURES_SEED_R3.jsonl`
- `CROSS_CITY_DONOR_DISTRIBUTION_REPORT.json`
- `BOUNDARY_AND_NO_ACTION_AUDIT.json`
- `SECRET_SCAN_REPORT.json`
- `HASH_MANIFEST.json`
- `CODEX_CLOSEOUT.md`

## Acceptance criteria

- Read-only consumption of Seed R3 preflight and all prior seed/product roots.
- At least 7 priority non-mobility domains represented.
- Barcelona, NYC, Chicago, and London represented where the preflight says they have fuel.
- WATCH / ASK / CHECK / BRIEF / SPATIAL fixtures generated.
- Event replay rows generated.
- Data-quality/maturity fixtures generated.
- Every row carries `source_class`, `truth_layer`, `donor_refs`, and `limitation_refs`.
- Cross-city data is donor/context only, not Dubai truth.
- No human/person-level records.
- No credentials.
- No raw bulky data.
- No public API, production frontend, live monitoring, dispatch, control, enforcement, legal, or certified claim.

## Notes

The generated Seed R3 refresh should complement Seed R2, not replace it. It should not mutate Seed R1, Seed R2, Product Consumption R1, D5 runtime integration, or D6 control-room outputs.
