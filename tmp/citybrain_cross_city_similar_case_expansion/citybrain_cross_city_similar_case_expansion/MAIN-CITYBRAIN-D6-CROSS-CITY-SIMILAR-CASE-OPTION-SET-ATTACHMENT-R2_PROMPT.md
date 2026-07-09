# MAIN-CITYBRAIN-D6-CROSS-CITY-SIMILAR-CASE-OPTION-SET-ATTACHMENT-R2

## Objective
Attach selected cross-city similar-case refs to existing reviewed option sets without redefining the option-set schema.

## Required upstream discovery
Find the latest green upstreams from the existing `outputs/` ledger. If required upstreams are missing, fail safely and write the missing upstreams in the decision JSON.

## Scope
Attach only as context fields; preserve execution_state = not_executed.


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
`outputs/main_citybrain_d6_cross_city_similar_case_option_set_attachment_r2/`

## Required artifacts
- `MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_OPTION_SET_ATTACHMENT_R2_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `VALIDATION_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`
- `OPTION_SET_SIMILAR_CASE_ATTACHMENTS.json`
- `ATTACHMENT_SCHEMA_COMPATIBILITY_REPORT.json`
- `ATTACHMENT_LIMITATIONS_LEDGER.md`

## Pass condition
Pass only if required upstreams are found/green, all JSON/JSONL parse cleanly, boundary/no-action/no-mutation/secret/hash audits pass, and no unsupported production/action/legal/certified claim is introduced.

## Final status
`PASS_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_OPTION_SET_ATTACHMENT_R2_WITH_LIMITATIONS`

## Failure status
`FAIL_MAIN_CITYBRAIN_D6_CROSS_CITY_SIMILAR_CASE_OPTION_SET_ATTACHMENT_R2`
