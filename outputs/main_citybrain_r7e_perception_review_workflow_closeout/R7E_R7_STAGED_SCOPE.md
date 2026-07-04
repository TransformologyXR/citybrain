# R7 Staged Scope

Package: `MAIN-CITYBRAIN-R7-COMMIT-AND-PUSH`

Branch: `ask-v11-canonical-implementation-sprint`

Commit message:

```text
Add R7 local replay perception-to-review workflow
```

## Staged File List

- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/ACTION_PROPOSAL_BOUNDARY_AUDIT.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/BOUNDARY_AUDIT.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/CANDIDATE_OBSERVATION_INGRESS_AUDIT.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/CASE_TICKET_DRAFT_ADAPTER_AUDIT.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/CHECK_CLAIMABILITY_AUDIT.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/DECISION.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/ENTRY_PROMPT.md`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/HASH_MANIFEST.txt`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/HUMAN_REVIEW_PROMOTION_GATE_AUDIT.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/LIMITATIONS.md`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/ONE_TRUTH_PACKET_AUDIT.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/PERCEPTION_SOURCE_PROVENANCE_AUDIT.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/README.md`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/TEST_LOG.txt`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/WEBUI_KIT_REVIEW_SURFACE_AUDIT.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/action_proposals/action_proposals.jsonl`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/action_proposals/prohibited_autonomy_audit.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/candidate_observations/candidate_observation_event_packets.jsonl`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/candidate_observations/candidate_observations.jsonl`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/citybrain_r7_perception_to_review_workflow_preflight.zip`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/draft_workflow_packets/draft_case_ticket_examples.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/draft_workflow_packets/draft_case_ticket_packets.jsonl`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/draft_workflow_packets/review_promotions.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/fixtures/action_proposal_schema.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/fixtures/camera_source_registry.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/fixtures/candidate_observation_schema.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/fixtures/draft_case_ticket_schema.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/fixtures/review_promotion_schema.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/kit_evidence/kit_review_packets.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/kit_evidence/review_overlay_packet_refs.json`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/source_refs/kit_refs.txt`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/source_refs/perception_adapter_refs.txt`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/source_refs/runner_ref.txt`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/source_refs/webui_refs.txt`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/webui_evidence/review_surface_snapshot.html`
- `outputs/main_citybrain_r7_perception_to_review_workflow_preflight/webui_evidence/webui_review_packets.json`
- `outputs/main_citybrain_r7a_perception_candidate_observation_ingress/R7A_ACCEPTED_REVIEW_EVENTS.json`
- `outputs/main_citybrain_r7a_perception_candidate_observation_ingress/R7A_AUDIT_REPORT.json`
- `outputs/main_citybrain_r7a_perception_candidate_observation_ingress/R7A_CANDIDATE_OBSERVATION_FIXTURES.json`
- `outputs/main_citybrain_r7a_perception_candidate_observation_ingress/R7A_CANDIDATE_OBSERVATION_INGRESS_DECISION.json`
- `outputs/main_citybrain_r7a_perception_candidate_observation_ingress/R7A_HASH_MANIFEST.json`
- `outputs/main_citybrain_r7a_perception_candidate_observation_ingress/R7A_KIT_REVIEW_EXPORT.json`
- `outputs/main_citybrain_r7a_perception_candidate_observation_ingress/R7A_LIMITATIONS.md`
- `outputs/main_citybrain_r7a_perception_candidate_observation_ingress/R7A_QUARANTINED_OBSERVATIONS.json`
- `outputs/main_citybrain_r7a_perception_candidate_observation_ingress/R7A_TEST_LOG.md`
- `outputs/main_citybrain_r7a_perception_candidate_observation_ingress/R7A_UNRESOLVED_OBSERVATIONS.json`
- `outputs/main_citybrain_r7a_perception_candidate_observation_ingress/R7A_WEBUI_REVIEW_EXPORT.json`
- `outputs/main_citybrain_r7b_perception_to_event_fabric_local_replay/R7B_BOUNDARY_AUDIT.json`
- `outputs/main_citybrain_r7b_perception_to_event_fabric_local_replay/R7B_EVENT_FABRIC_DECISION.json`
- `outputs/main_citybrain_r7b_perception_to_event_fabric_local_replay/R7B_EVENT_STATE_QUERY_FIXTURES.json`
- `outputs/main_citybrain_r7b_perception_to_event_fabric_local_replay/R7B_HASH_MANIFEST.json`
- `outputs/main_citybrain_r7b_perception_to_event_fabric_local_replay/R7B_KIT_EVENT_OVERLAY_EXPORT.json`
- `outputs/main_citybrain_r7b_perception_to_event_fabric_local_replay/R7B_LIMITATIONS.md`
- `outputs/main_citybrain_r7b_perception_to_event_fabric_local_replay/R7B_LOCAL_EVENT_LOG.jsonl`
- `outputs/main_citybrain_r7b_perception_to_event_fabric_local_replay/R7B_MATERIALIZED_REVIEW_STATE.json`
- `outputs/main_citybrain_r7b_perception_to_event_fabric_local_replay/R7B_REPLAY_REPORT.json`
- `outputs/main_citybrain_r7b_perception_to_event_fabric_local_replay/R7B_TEST_LOG.md`
- `outputs/main_citybrain_r7b_perception_to_event_fabric_local_replay/R7B_WEBUI_EVENT_OVERLAY_EXPORT.json`
- `outputs/main_citybrain_r7c_event_fabric_state_query_and_ask_handoff/R7C_ASK_HANDOFF_EVIDENCE_PACKETS.json`
- `outputs/main_citybrain_r7c_event_fabric_state_query_and_ask_handoff/R7C_ASK_HANDOFF_FIXTURES.json`
- `outputs/main_citybrain_r7c_event_fabric_state_query_and_ask_handoff/R7C_BOUNDARY_AUDIT.json`
- `outputs/main_citybrain_r7c_event_fabric_state_query_and_ask_handoff/R7C_EVENT_STATE_QUERY_AND_ASK_HANDOFF_DECISION.json`
- `outputs/main_citybrain_r7c_event_fabric_state_query_and_ask_handoff/R7C_EVENT_STATE_QUERY_CASES.json`
- `outputs/main_citybrain_r7c_event_fabric_state_query_and_ask_handoff/R7C_EVENT_STATE_QUERY_RESULTS.json`
- `outputs/main_citybrain_r7c_event_fabric_state_query_and_ask_handoff/R7C_HASH_MANIFEST.json`
- `outputs/main_citybrain_r7c_event_fabric_state_query_and_ask_handoff/R7C_KIT_QUERY_CONTEXT_EXPORT.json`
- `outputs/main_citybrain_r7c_event_fabric_state_query_and_ask_handoff/R7C_LIMITATIONS.md`
- `outputs/main_citybrain_r7c_event_fabric_state_query_and_ask_handoff/R7C_TEST_LOG.md`
- `outputs/main_citybrain_r7c_event_fabric_state_query_and_ask_handoff/R7C_WEBUI_QUERY_CONTEXT_EXPORT.json`
- `outputs/main_citybrain_r7d_webui_kit_event_state_smoke/R7D_BOUNDARY_AUDIT.json`
- `outputs/main_citybrain_r7d_webui_kit_event_state_smoke/R7D_HASH_MANIFEST.json`
- `outputs/main_citybrain_r7d_webui_kit_event_state_smoke/R7D_KIT_EVENT_STATE_SMOKE.usda`
- `outputs/main_citybrain_r7d_webui_kit_event_state_smoke/R7D_KIT_EVENT_STATE_SMOKE_EXPORT.json`
- `outputs/main_citybrain_r7d_webui_kit_event_state_smoke/R7D_KIT_EVENT_STATE_SMOKE_MANIFEST.json`
- `outputs/main_citybrain_r7d_webui_kit_event_state_smoke/R7D_LIMITATIONS.md`
- `outputs/main_citybrain_r7d_webui_kit_event_state_smoke/R7D_TEST_LOG.md`
- `outputs/main_citybrain_r7d_webui_kit_event_state_smoke/R7D_WEBUI_EVENT_STATE_SMOKE_EXPORT.json`
- `outputs/main_citybrain_r7d_webui_kit_event_state_smoke/R7D_WEBUI_EVENT_STATE_SMOKE_FIXTURE.json`
- `outputs/main_citybrain_r7d_webui_kit_event_state_smoke/R7D_WEBUI_KIT_EVENT_STATE_SMOKE_DECISION.json`
- `outputs/main_citybrain_r7d_webui_kit_event_state_smoke/R7D_WEBUI_KIT_PARITY_REPORT.json`
- `outputs/main_citybrain_r7e_perception_review_workflow_closeout/R7E_BOUNDARY_AND_NON_CLAIMS.md`
- `outputs/main_citybrain_r7e_perception_review_workflow_closeout/R7E_COMMIT_AND_PUSH_PROMPT.md`
- `outputs/main_citybrain_r7e_perception_review_workflow_closeout/R7E_HASH_MANIFEST.json`
- `outputs/main_citybrain_r7e_perception_review_workflow_closeout/R7E_LIMITATIONS_AND_NEXT_STEPS.md`
- `outputs/main_citybrain_r7e_perception_review_workflow_closeout/R7E_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT_DECISION.json`
- `outputs/main_citybrain_r7e_perception_review_workflow_closeout/R7E_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT_SUMMARY.md`
- `outputs/main_citybrain_r7e_perception_review_workflow_closeout/R7E_R7_PACKAGE_LEDGER.md`
- `outputs/main_citybrain_r7e_perception_review_workflow_closeout/R7E_TEST_COMMANDS.md`
- `outputs/main_citybrain_r7e_perception_review_workflow_closeout/R7E_R7_STAGED_SCOPE.md`
- `scripts/run_main_citybrain_r7_perception_to_review_workflow_preflight.py`
- `scripts/run_main_citybrain_r7a_perception_candidate_observation_ingress.py`
- `scripts/run_main_citybrain_r7b_perception_to_event_fabric_local_replay.py`
- `scripts/run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py`
- `scripts/run_main_citybrain_r7d_webui_kit_event_state_smoke.py`
- `scripts/run_main_citybrain_r7e_perception_review_workflow_closeout.py`
- `tests/test_main_citybrain_r7_perception_to_review_workflow_preflight.py`
- `tests/test_main_citybrain_r7a_perception_candidate_observation_ingress.py`
- `tests/test_main_citybrain_r7b_perception_to_event_fabric_local_replay.py`
- `tests/test_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py`
- `tests/test_main_citybrain_r7d_webui_kit_event_state_smoke.py`
- `tests/test_main_citybrain_r7e_perception_review_workflow_closeout.py`

## Included Categories

- R7 preflight outputs and runner/test.
- R7A candidate-observation ingress outputs and runner/test.
- R7B local/replay event fabric outputs and runner/test.
- R7C event-state query and ASK handoff outputs and runner/test.
- R7D WebUI/Kit event-state smoke outputs and runner/test.
- R7E closeout outputs and runner/test.

## Excluded Categories

- `apps/` and ASK app fixture vendoring work.
- Non-R7 outputs.
- Non-R7 scripts and tests.
- ASK runtime files and sealed eval drift.
- `corpus_raw/`, `inputs/`, `tmp/`, loose text files, handoff folders, Omniverse/Metropolis unrelated work, and unrelated deleted zips.

## Test Results

- R7E focused unittest: PASS, 11 tests.
- R7D focused unittest: PASS, 17 tests.
- R7C focused unittest: PASS, 15 tests.
- R7B focused unittest: PASS, 12 tests.
- R7A focused unittest: PASS, 13 tests.
- Full unittest discovery: PASS, 332 tests.
- ASK runtime scoped diff: empty.

## Hash Manifest

- R7E hash manifest: PASS, 29 items, 0 missing, 0 mismatch.

## Limitations

- R7 remains local/replay only.
- Candidate observations remain review inputs, not official facts.
- Sandbox case/ticket outputs remain draft_not_submitted.
- Action proposals remain not_executed.
- WebUI/Kit outputs remain review-safe fixture exports, not production integrations.
- No live retrieval, production API, URL fetch, LLM call, official submission, dispatch/control/enforcement, legal/certified claim, full citywide twin, live Kit control, or ASK runtime change.
