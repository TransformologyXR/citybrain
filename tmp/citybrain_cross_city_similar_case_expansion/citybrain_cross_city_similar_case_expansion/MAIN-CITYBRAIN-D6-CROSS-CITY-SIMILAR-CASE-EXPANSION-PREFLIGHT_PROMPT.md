# MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-EXPANSION-PREFLIGHT

## Objective
Define the bounded cross-city similar-case expansion scope from the scout output. Select case families, source cities, required artifacts, and no-overclaim boundaries.

## Required upstream discovery
Find the latest green upstreams from the existing `outputs/` ledger. If required upstreams are missing, fail safely and write the missing upstreams in the decision JSON.

## Scope
Read-only preflight. No ingestion, no download, no runtime implementation.


Boundary to preserve:
- local/replay/review/query context only
- no production/public API claim
- no autonomous monitoring or alerts
- no dispatch, routing/control, enforcement, official ticket/case, legal/certified finding, or automated action
- no mutation of frozen upstream outputs
- no secret leakage
- Track D remains authoritative for approval lifecycle after human promotion
- all generated outputs must include claim-boundary, no-action, no-mutation, secret, hash, validation, and local open index artifacts


## Required output root
Use:
`outputs/main_citybrain_d6_cross_city_similar_case_expansion_preflight/`

## Required artifacts
- `MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_PREFLIGHT_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `VALIDATION_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`
- `SIMILAR_CASE_EXPANSION_SCOPE.md`
- `SOURCE_CITY_DOMAIN_MATRIX.json`
- `BOUNDARY_AND_LIMITATION_PLAN.md`

## Pass condition
Pass only if required upstreams are found/green, all JSON/JSONL parse cleanly, boundary/no-action/no-mutation/secret/hash audits pass, and no unsupported production/action/legal/certified claim is introduced.

## Final status
`PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_PREFLIGHT_WITH_LIMITATIONS`

## Failure status
`FAIL_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_EXPANSION_PREFLIGHT`
