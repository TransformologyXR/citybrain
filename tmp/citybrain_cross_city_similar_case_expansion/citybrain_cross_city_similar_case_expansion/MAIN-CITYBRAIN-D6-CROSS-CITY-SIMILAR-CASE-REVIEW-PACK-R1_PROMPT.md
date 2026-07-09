# MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-REVIEW-PACK-R1

## Objective
Build a bounded review pack of cross-city similar cases using existing accepted artifacts only.

## Required upstream discovery
Find the latest green upstreams from the existing `outputs/` ledger. If required upstreams are missing, fail safely and write the missing upstreams in the decision JSON.

## Scope
Cases must be clearly labelled as context and not recommendations, mandates, or precedent.


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
`outputs/main_citybrain_d6_cross_city_similar_case_review_pack_r1/`

## Required artifacts
- `MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_REVIEW_PACK_R1_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `VALIDATION_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`
- `CROSS_CITY_SIMILAR_CASE_REVIEW_PACK.json`
- `CROSS_CITY_SIMILAR_CASE_REVIEW_PACK.jsonl`
- `CASE_SOURCE_TRACE.json`
- `CASE_LIMITATIONS_LEDGER.md`

## Pass condition
Pass only if required upstreams are found/green, all JSON/JSONL parse cleanly, boundary/no-action/no-mutation/secret/hash audits pass, and no unsupported production/action/legal/certified claim is introduced.

## Final status
`PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_REVIEW_PACK_R1_WITH_LIMITATIONS`

## Failure status
`FAIL_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_REVIEW_PACK_R1`
