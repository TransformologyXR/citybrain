# PACKAGE — MAIN-CITYBRAIN-R7-PERCEPTION-TO-REVIEW-WORKFLOW-PREFLIGHT

## Output root

```text
outputs/main_citybrain_r7_perception_to_review_workflow_preflight/
```

## ZIP

```text
citybrain_r7_perception_to_review_workflow_preflight.zip
```

## Expected structure

```text
outputs/main_citybrain_r7_perception_to_review_workflow_preflight/
├── ENTRY_PROMPT.md
├── README.md
├── DECISION.json
├── CANDIDATE_OBSERVATION_INGRESS_AUDIT.json
├── PERCEPTION_SOURCE_PROVENANCE_AUDIT.json
├── CHECK_CLAIMABILITY_AUDIT.json
├── HUMAN_REVIEW_PROMOTION_GATE_AUDIT.json
├── CASE_TICKET_DRAFT_ADAPTER_AUDIT.json
├── ACTION_PROPOSAL_BOUNDARY_AUDIT.json
├── WEBUI_KIT_REVIEW_SURFACE_AUDIT.json
├── ONE_TRUTH_PACKET_AUDIT.json
├── BOUNDARY_AUDIT.json
├── LIMITATIONS.md
├── TEST_LOG.txt
├── HASH_MANIFEST.txt
├── fixtures/
│   ├── camera_source_registry.json
│   ├── candidate_observation_schema.json
│   ├── review_promotion_schema.json
│   ├── draft_case_ticket_schema.json
│   └── action_proposal_schema.json
├── candidate_observations/
│   ├── candidate_observations.jsonl
│   └── candidate_observation_event_packets.jsonl
├── draft_workflow_packets/
│   ├── draft_case_ticket_packets.jsonl
│   └── draft_case_ticket_examples.json
├── action_proposals/
│   ├── action_proposals.jsonl
│   └── prohibited_autonomy_audit.json
├── webui_evidence/
│   └── review_surface_snapshot.html
├── kit_evidence/
│   └── review_overlay_packet_refs.json
└── source_refs/
    ├── perception_adapter_refs.txt
    ├── webui_refs.txt
    ├── kit_refs.txt
    └── runner_ref.txt
```

## DECISION.json minimum fields

```json
{
  "task_id": "MAIN-CITYBRAIN-R7-PERCEPTION-TO-REVIEW-WORKFLOW-PREFLIGHT",
  "status": "PASS_R7E_PERCEPTION_TO_REVIEW_WORKFLOW_SMOKE_WITH_LIMITATIONS",
  "perception_candidate_observation_ingress": "PASS | PARTIAL | FAIL",
  "human_review_promotion_gate": "PASS | PARTIAL | FAIL",
  "case_ticket_draft_adapter": "PASS | PARTIAL | FAIL",
  "action_proposal_boundary": "PASS | PARTIAL | FAIL",
  "webui_kit_review_surface": "PASS | PARTIAL | FAIL",
  "candidate_observation_count": 0,
  "draft_case_ticket_count": 0,
  "action_proposal_count": 0,
  "official_submission_performed": false,
  "autonomous_action_performed": false,
  "execution_status": "not_executed",
  "one_truth_packet_audit": "PASS | FAIL",
  "boundary_audit": "PASS | FAIL",
  "forbidden_claims_present": false,
  "tests": {
    "targeted_r7": "PASS | FAIL",
    "full_discovery": "PASS | FAIL",
    "test_count": 0
  },
  "limitations": []
}
```
