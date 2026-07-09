# ENTRY PROMPT — Governed 9-Stage Runtime Contract Smoke R1

Task: `MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-CONTRACT-SMOKE-R1`

You are running the governed 9-stage runtime contract smoke for the current Decision-Support Intelligence Sprint.

Do not start unless `MAIN-CITYBRAIN-D6-CROSS-DOMAIN-CASCADE-CLOSEOUT` and preferably `MAIN-CITYBRAIN-D6-CROSS-DOMAIN-CASCADE-MILESTONE-FREEZE` are green. If Cross-Domain Cascade is missing or not green, fail safely with upstream_missing and do not create a partial smoke.

Goal:
Prove that the existing decision-support artifacts can be passed through a governed 9-stage state-machine contract without becoming nine autonomous LLM gates and without creating any real-world action. This is contract smoke only, not a production runtime.

Stages:
1. RECALL — deterministic load of scenario, option sets, evidence, refs, and prior artifacts.
2. PLAN — deterministic selection of the bounded review workflow.
3. VALIDATE_PLAN — schema, boundary, review-state, and quality gate checks.
4. EXECUTE — local/replay fixture reads and simulator/optimizer/retrieval/cascade artifact calls only; no real-world action.
5. NORMALIZE — normalize outputs into `reviewed_option_set` / display packet / trace contracts.
6. SYNTHESIZE — one grounded narration-eligible stage only, based on evidence and option-set refs.
7. RESOLVE_ACTIONS — map only to Track D proposal bridge candidates; no approval/execution.
8. SUGGEST — safe next-look/review-only suggestions only.
9. COMPLETE — final trace, audit, limitation, hash, and handoff summary.

Inputs to discover:
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CONTRACT-SPINE-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-PLAN-MODE-SUMO-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-SIMILAR-CASE-RETRIEVAL-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-INVERSE-DYNAMICS-MULTI-OPTION-MILESTONE-FREEZE`
- `MAIN-CITYBRAIN-D6-DECISION-SUPPORT-CERTIFIED-STATE-AND-HANDOVER-REFRESH`
- `MAIN-CITYBRAIN-D6-CROSS-DOMAIN-CASCADE-CLOSEOUT`
- `MAIN-CITYBRAIN-D6-CROSS-DOMAIN-CASCADE-MILESTONE-FREEZE` if present
- Track D HITL reviewed-action milestone freeze

Produce output root:
`outputs/main_citybrain_d6_governed_9_stage_runtime_contract_smoke_r1/`

Create runner:
`scripts/run_main_citybrain_d6_governed_9_stage_runtime_contract_smoke_r1.py`

Required output files:
- `MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_CONTRACT_SMOKE_R1_DECISION.json`
- `README.md`
- `LOCAL_OPEN_INDEX.md`
- `INPUT_ARTIFACT_INDEX.json`
- `NINE_STAGE_RUNTIME_CONTRACT.json`
- `NINE_STAGE_STAGE_IO_MATRIX.json`
- `NINE_STAGE_SMOKE_FIXTURES.json`
- `NINE_STAGE_SMOKE_RESULTS.json`
- `MODEL_USAGE_POLICY.json`
- `RESOLVE_ACTIONS_TRACK_D_BOUNDARY.json`
- `TRACE_AUDIT_CONTRACT.json`
- `NEGATIVE_TEST_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`

Required negative tests:
- reject/flag any stage plan that requires nine LLM calls
- reject/flag autonomous agent swarm interpretation
- reject/flag auto-execute payload
- reject/flag dispatch/routing/control/enforcement/legal/certified actions
- reject/flag ungrounded synthesis without evidence refs
- reject/flag proposal approval outside Track D

Decision status on success:
`PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_CONTRACT_SMOKE_R1_WITH_LIMITATIONS`

Decision status on failure:
`FAIL_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_CONTRACT_SMOKE_R1`

After completion, report status, output root, stage count, fixture count, negative test count, upstreams found/required, blocking gaps, non-blocking gaps, and next recommended task.
