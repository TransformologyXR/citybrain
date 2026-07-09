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


Task: `MAIN-CITYBRAIN-D6-CROSS-DOMAIN-CASCADE-OPTION-SET-ATTACHMENT-R3`

Objective:
Attach cascade findings to Track S reviewed option sets without redefining the reviewed_option_set schema or Track D proposal lifecycle.

Rules:
- preserve `execution_state = not_executed`
- preserve `human_review_required = true`
- no Track D promotion
- no approval state ownership
- option-set cascade attachments are evidence/context only

Outputs:
- `CASCADE_OPTION_SET_ATTACHMENTS.json`
- `CASCADE_OPTION_SET_ATTACHMENT_VALIDATION.json`
- `REVIEWED_OPTION_SET_COMPATIBILITY_REPORT.json`
- `TRACK_D_BOUNDARY_PRESERVATION_AUDIT.json`
- standard decision/audits/hash/local index

Expected pass status:
`PASS_MAIN_CITYBRAIN_D6_CROSS_DOMAIN_CASCADE_OPTION_SET_ATTACHMENT_R3_WITH_LIMITATIONS`
