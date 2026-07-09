You are Codex working in the local CityBrain repo.

Obey the project boundary:
- local/replay review/query context only
- no production/public API
- no autonomous monitoring
- no alerts
- no dispatch
- no routing/control
- no enforcement
- no legal/certified finding
- no official ticket/case creation
- no automated action
- no mutation of prior output roots

Use additive outputs under `outputs/`.
Create or update only the runner for this task and new output artifacts.
Preserve unrelated worktree changes.


Task: `MAIN-CITYBRAIN-D6-CROSS-DOMAIN-CASCADE-PATH-CATALOG-R1`

Objective:
Build a read-only catalog of candidate cascade paths from existing R7/R8/CERSEG/Incident/Hero/Option-Set artifacts.

Do not add edges. Do not change R7/R8. Do not promote scene refs to canonical IDs.

Path examples:
- event -> corridor asset -> road/lane context -> mobility impact context
- event -> affected asset -> building/property/planning context
- event -> operator-surface packet -> reviewed option set
- option set -> similar cases -> cross-city evidence context
- option set -> HITL proposal eligibility context

Outputs:
- `CASCADE_PATH_CATALOG.json`
- `CASCADE_PATH_CATALOG.jsonl`
- `CASCADE_PATH_COVERAGE_MATRIX.json`
- `CASCADE_PATH_VALIDATION_REPORT.json`
- standard decision/audits/hash/local index

Expected pass status:
`PASS_MAIN_CITYBRAIN_D6_CROSS_DOMAIN_CASCADE_PATH_CATALOG_R1_WITH_LIMITATIONS`
