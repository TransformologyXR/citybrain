# ASK v1.1 Commit Scope

Package: ASK-V11-REPO-COMMIT-AND-PR-PREP
Status: PASS_WITH_LIMITATIONS
Final sprint decision: PASS_ASK_V11_CANONICAL_IMPLEMENTATION_SPRINT

## Scope Rule

This source-control prep package is documentation and review prep only. It does not implement new runtime behavior, change router behavior, change packet schemas, change registries/templates, change CHECK or renderer behavior, add future-flow runtime, add live retrieval, add a production API, or add official action/ticket/dispatch behavior.

## Files Proposed For Commit

ASK v1.1 implementation:

- packages/ask_v11/__init__.py
- packages/ask_v11/answer_assembly.py
- packages/ask_v11/argument_resolution.py
- packages/ask_v11/boundary.py
- packages/ask_v11/checks.py
- packages/ask_v11/compiler.py
- packages/ask_v11/concept_bindings.py
- packages/ask_v11/eval.py
- packages/ask_v11/eval_cases.py
- packages/ask_v11/fixtures.py
- packages/ask_v11/full_spine.py
- packages/ask_v11/future_flow_skeletons.py
- packages/ask_v11/packets.py
- packages/ask_v11/registries.py
- packages/ask_v11/registry_seed.py
- packages/ask_v11/render_validation.py
- packages/ask_v11/rendering.py
- packages/ask_v11/resolver.py
- packages/ask_v11/severity.py
- packages/ask_v11/spine.py
- packages/ask_v11/template_execution.py
- packages/ask_v11/templates.py

Contracts and runners:

- packages/contracts/ask_v11_packets.schema.json
- scripts/emit_ask_v11_packet_schema.py
- scripts/run_ask_v11_sealed_eval.py

ASK v1.1 tests:

- tests/test_ask_v11_eval_sealing.py
- tests/test_ask_v11_future_flow_skeletons.py
- tests/test_ask_v11_g1_g5_spine.py
- tests/test_ask_v11_g6_g8_check_answer_render.py
- tests/test_ask_v11_packets.py
- tests/test_ask_v11_registries.py

ASK v1.1 docs:

- docs/ask-v11/ask-v11-implementation-closeout.md
- docs/ask-v11/eval-sealing-and-skeleton-flows.md
- docs/ask-v11/g1-g5-execution-spine.md
- docs/ask-v11/g6-g8-check-answer-render.md
- docs/ask-v11/packet-discipline.md
- docs/ask-v11/registries-and-templates.md

Closeout and sealed-eval artifacts:

- outputs/ask_v11_closeout/ASK_V11_HASH_MANIFEST.json
- outputs/ask_v11_closeout/ASK_V11_IMPLEMENTATION_CLOSEOUT_DECISION.json
- outputs/ask_v11_closeout/ASK_V11_IMPLEMENTATION_CLOSEOUT_SUMMARY.md
- outputs/ask_v11_closeout/ASK_V11_IMPLEMENTATION_LEDGER.md
- outputs/ask_v11_closeout/ASK_V11_LIMITATIONS_AND_NEXT_STEPS.md
- outputs/ask_v11_closeout/ASK_V11_TEST_COMMANDS.md
- outputs/ask_v11_sealed_eval/ASK_V11_SEALED_EVAL_REPORT.json
- outputs/ask_v11_sealed_eval/ASK_V11_SEALED_EVAL_SUMMARY.md

Source-control prep artifacts:

- outputs/ask_v11_closeout/ASK_V11_COMMIT_SCOPE.md
- outputs/ask_v11_closeout/ASK_V11_PR_DRAFT.md
- outputs/ask_v11_closeout/ASK_V11_REVIEW_CHECKLIST.md

Note: outputs/ is ignored by .gitignore, so ASK output artifacts require explicit force-add if the user later chooses to stage them.

## Files Excluded

Unrelated pre-existing dirty files are excluded from this ASK commit scope, including:

- CITYBRAIN_OUTPUTS_DAY_BY_DAY_FORENSIC_2026-06-30.md
- CITYBRAIN_WORKSPACE_CHRONOLOGY_LINEAGE_2026-06-30.md
- outputs/main_citybrain_d6_hero_usd_twin_and_hitl_integration_readiness_review.zip
- scripts/citybrain_track_p_packaging_common.py
- CITYBRAIN_CHRONOLOGY_TRACE_DELTA_2026-07-01.md
- CITYBRAIN_CHRONOLOGY_TRACE_DELTA_2026-07-02.md
- CITYBRAIN_FINAL_UPDATE_2026-07-01.md
- CITYBRAIN_OUTPUTS_TRACE_AND_AUDIT_CHRONOLOGY_2026-07-01.md
- CITYBRAIN_PRODUCT_EVOLUTION_STORY_2026-07-01.md
- CITYBRAIN_WORKSPACE_CHRONOLOGY_LINEAGE_2026-07-01.md
- ORCHESTRATOR EVOLUTION OLD CODE.MD
- apps/
- corpus_raw/
- inputs/
- tmp/
- _handoff_*/
- non-ASK scripts under scripts/
- non-ASK tests under tests/
- Metropolis/VSS scripts and outputs
- Omniverse/WebRTC scripts and tests
- text 1.txt, text2.txt, text 3.txt, text 4.txt, text 5.txt, text 6.txt

Unknown / needs human review:

- tests/__init__.py, because it is a generic test package marker and not part of the explicit tests/test_ask_v11_*.py scope.
- packages/contracts/ non-ASK schemas, because only packages/contracts/ask_v11_packets.schema.json is in ASK scope.

## Commands Run

- git status --short
- git status --short -- packages/ask_v11 packages/contracts/ask_v11_packets.schema.json scripts/emit_ask_v11_packet_schema.py scripts/run_ask_v11_sealed_eval.py tests docs/ask-v11 outputs/ask_v11_sealed_eval outputs/ask_v11_closeout
- git status --short --untracked-files=all -- packages/ask_v11 packages/contracts/ask_v11_packets.schema.json scripts/emit_ask_v11_packet_schema.py scripts/run_ask_v11_sealed_eval.py tests docs/ask-v11 outputs/ask_v11_sealed_eval outputs/ask_v11_closeout
- git check-ignore -v outputs/ask_v11_closeout/ASK_V11_IMPLEMENTATION_CLOSEOUT_DECISION.json outputs/ask_v11_sealed_eval/ASK_V11_SEALED_EVAL_REPORT.json outputs/ask_v11_closeout/ASK_V11_HASH_MANIFEST.json
- .venv\Scripts\python.exe -m unittest tests.test_ask_v11_packets
- .venv\Scripts\python.exe -m unittest tests.test_ask_v11_registries
- .venv\Scripts\python.exe -m unittest tests.test_ask_v11_g1_g5_spine
- .venv\Scripts\python.exe -m unittest tests.test_ask_v11_g6_g8_check_answer_render
- .venv\Scripts\python.exe -m unittest tests.test_ask_v11_eval_sealing
- .venv\Scripts\python.exe -m unittest tests.test_ask_v11_future_flow_skeletons
- .venv\Scripts\python.exe scripts\run_ask_v11_sealed_eval.py
- PowerShell SHA-256 verification of outputs/ask_v11_closeout/ASK_V11_HASH_MANIFEST.json

## Test Results

- P0 packets: 14 passed
- P1 registries: 19 passed
- P2 spine: 32 passed
- P3 CHECK/answer/render: 40 passed
- P4 eval sealing: 22 passed
- P4 skeleton flows: 13 passed
- Sealed eval CLI: PASS

## Sealed Eval Result

- final_decision: PASS_ASK_V11_SEALED_EVAL
- total_cases: 21
- pass_count: 21
- fail_count: 0
- sev_4_real_failure: 0
- boundary_action_sev4_count: 0
- future_flow_runtime_violation_count: 0
- raw_query_leak_count: 0
- official_action_claim_count: 0

## Hash Manifest Status

Status recorded: resolved by ASK-V11-HASH-MANIFEST-RECONCILE-AND-COMMIT-PREP.

The closeout hash manifest now matches the current artifact state, including the regenerated sealed eval report and the source-control prep documents.

- path: outputs/ask_v11_sealed_eval/ASK_V11_SEALED_EVAL_REPORT.json
- current: 674941af02d3a842cc153eb34510fae641ceda9de55648d0b536bc707d16f281

If scripts/run_ask_v11_sealed_eval.py is rerun after this reconciliation, refresh the closeout hash manifest intentionally before final staging.

## Risk Notes

- The workspace has a very large unrelated dirty tree. The ASK commit should be staged by explicit path only.
- outputs/ is ignored by .gitignore. Closeout, sealed-eval, and prep output artifacts require explicit force-add if included.
- The sealed eval report contains a generated_at timestamp and can drift when rerun.
- Future flows remain skeleton-only and should not be expanded in this commit.

## Recommended Branch

ask-v11-canonical-implementation-sprint

## Recommended Commit Message

Implement ASK v1.1 canonical packet flow and sealed eval

Commit body:

- Add ASK v1.1 packet/envelope contracts and JSON Schema.
- Add Concept-Binding Registry and Template Registry.
- Add deterministic G1-G5 ASK execution spine.
- Add deterministic G6 CHECK engine, G7 AnswerPacket assembly, and G8 render validator.
- Add sealed eval with Severity 0-4 reporting.
- Add WATCH/BRIEF/DIFF/INCIDENT skeleton-only contract tests.
- Add closeout artifacts and hash manifest.
- Preserve fixture/local scope; no live retrieval, production API, official actions, or future-flow runtime.
