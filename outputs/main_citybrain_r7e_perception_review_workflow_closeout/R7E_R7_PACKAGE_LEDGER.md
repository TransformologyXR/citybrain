# R7 Package Ledger

## R7 - perception-to-review workflow preflight

- status: `PASS_R7E_PERCEPTION_TO_REVIEW_WORKFLOW_SMOKE_WITH_LIMITATIONS`
- summary: Established candidate observation, event packet, human review promotion, sandbox draft case/ticket, action proposal, and WebUI/Kit review export boundaries.
- counts: `{"action_proposals": 1, "candidate_observations": 1, "draft_case_tickets": 1, "event_packets": 1, "kit_packets": 1, "review_promotions": 1, "webui_packets": 1}`

## R7A - perception candidate observation ingress

- status: `PASS_MAIN_CITYBRAIN_R7A_PERCEPTION_CANDIDATE_OBSERVATION_INGRESS_WITH_LIMITATIONS`
- summary: Ingested local/replay candidate observations and preserved accepted, unresolved, and quarantined paths with WebUI/Kit review packet exports.
- counts: `{"accepted_review_events": 1, "candidate_observations_total": 5, "kit_exports": 3, "quarantined_observations": 2, "unresolved_observations": 2, "webui_exports": 3}`

## R7B - perception to event fabric local replay

- status: `PASS_MAIN_CITYBRAIN_R7B_PERCEPTION_TO_EVENT_FABRIC_LOCAL_REPLAY_WITH_LIMITATIONS`
- summary: Created append-only local event log, deterministic replay, materialized review state, and WebUI/Kit event overlay exports.
- counts: `{"active_review_events": 1, "event_log_entries": 8, "kit_event_overlays": 6, "not_executed_action_proposals": 1, "quarantined_observations": 2, "replayed_events": 8, "sandbox_draft_cases": 1, "unresolved_observations": 2, "webui_event_overlays": 6}`

## R7C - event fabric state query and ASK handoff

- status: `PASS_MAIN_CITYBRAIN_R7C_EVENT_FABRIC_STATE_QUERY_AND_ASK_HANDOFF_WITH_LIMITATIONS`
- summary: Closed event-state query families, ASK-safe handoff fixtures, EvidencePacket-shaped outputs, and WebUI/Kit query context exports.
- counts: `{"ask_handoff_evidence_packets": 8, "ask_handoff_fixtures": 8, "kit_query_context_exports": 8, "query_cases": 8, "query_results": 8, "webui_query_context_exports": 8}`

## R7D - WebUI/Kit event-state smoke

- status: `PASS_MAIN_CITYBRAIN_R7D_WEBUI_KIT_EVENT_STATE_SMOKE_WITH_LIMITATIONS`
- summary: Closed WebUI event-state smoke, Kit event-state smoke, marker-only USDA handoff, and WebUI/Kit one-truth parity.
- counts: `{"kit_smoke_items": 8, "optional_usda_created": true, "parity_failures": 0, "parity_pairs_checked": 8, "webui_smoke_items": 8}`
