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


Task: `MAIN-CITYBRAIN-D6-CROSS-DOMAIN-CASCADE-QUALITY-GATE-R4`

Objective:
Create and run a discriminating cascade quality gate.

Golden/negative cases must test:
- valid evidence-backed cascade path passes
- missing evidence ref fails or is quarantined
- unsupported domain claim blocked
- causal overclaim blocked
- unresolved/quarantined context preserved
- stale scenario state flagged
- action/control/dispatch wording blocked
- option-set attachment preserves not_executed and human_review_required
- no full citywide/certified cascade claim

Outputs:
- `CASCADE_GOLDEN_CASES.json`
- `CASCADE_QUALITY_GATE_RESULTS.json`
- `CASCADE_NEGATIVE_TEST_REPORT.json`
- standard decision/audits/hash/local index

Expected pass status:
`PASS_MAIN_CITYBRAIN_D6_CROSS_DOMAIN_CASCADE_QUALITY_GATE_R4_WITH_LIMITATIONS`
