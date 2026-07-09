# PACKAGE — MAIN-CITYBRAIN-R8-REAL-PERCEPTION-RUNTIME-AND-EVIDENCE-CLIP-INTEGRATION

## Output root

```text
outputs/main_citybrain_r8_real_perception_runtime_evidence_clip_integration/
```

## ZIP

```text
citybrain_r8_real_perception_runtime_evidence_clip_integration.zip
```

## Expected structure

```text
outputs/main_citybrain_r8_real_perception_runtime_evidence_clip_integration/
├── ENTRY_PROMPT.md
├── README.md
├── DECISION.json
├── PERCEPTION_SOURCE_REGISTRY_AUDIT.json
├── RUNTIME_ADAPTER_EXECUTION_REPORT.json
├── RUNTIME_DETECTION_METADATA_AUDIT.json
├── CANDIDATE_OBSERVATION_EXPORT_AUDIT.json
├── EVIDENCE_FRAME_CLIP_EXPORT_AUDIT.json
├── VSS_REVIEW_ASSIST_AUDIT.json
├── CHECK_CLAIMABILITY_AUDIT.json
├── WEBUI_KIT_REVIEW_INTEGRATION_AUDIT.json
├── DRAFT_WORKFLOW_BOUNDARY_AUDIT.json
├── ACTION_PROPOSAL_BOUNDARY_AUDIT.json
├── ONE_TRUTH_PACKET_AUDIT.json
├── BOUNDARY_AUDIT.json
├── LIMITATIONS.md
├── TEST_LOG.txt
├── HASH_MANIFEST.txt
├── source_media/
│   └── MEDIA_INVENTORY.json
├── runtime_logs/
│   └── runtime_execution.log
├── runtime_metadata/
│   └── runtime_detections.jsonl
├── candidate_observations/
│   ├── candidate_observations.jsonl
│   └── candidate_observation_event_packets.jsonl
├── evidence_frames/
│   ├── evidence_frame_manifest.json
│   └── frame_exports/
├── evidence_clips/
│   ├── evidence_clip_manifest.json
│   └── clip_exports/
├── vss_review_assist/
│   └── vss_review_assist_packets.jsonl
├── review_packets/
│   └── perception_review_packets.jsonl
├── draft_workflow_packets/
│   └── draft_case_ticket_packets.jsonl
├── action_proposals/
│   └── action_proposals.jsonl
├── webui_evidence/
│   └── perception_review_surface_snapshot.html
├── kit_evidence/
│   └── perception_overlay_packet_refs.json
└── source_refs/
    ├── deepstream_or_metropolis_refs.txt
    ├── vss_refs.txt
    ├── webui_refs.txt
    ├── kit_refs.txt
    └── runner_ref.txt
```

## DECISION.json minimum fields

```json
{
  "task_id": "MAIN-CITYBRAIN-R8-REAL-PERCEPTION-RUNTIME-AND-EVIDENCE-CLIP-INTEGRATION",
  "status": "PASS_R8F_REAL_PERCEPTION_RUNTIME_EVIDENCE_SMOKE_WITH_LIMITATIONS",
  "source_media_registered": true,
  "runtime_execution_status": "PASS | PARTIAL | BLOCKED | FAIL",
  "runtime_name": "DeepStream | Metropolis | VSS | fixture",
  "candidate_observation_count": 0,
  "evidence_frame_count": 0,
  "evidence_clip_count": 0,
  "vss_review_assist_count": 0,
  "webui_kit_review_surface": "PASS | PARTIAL | FAIL",
  "draft_case_ticket_count": 0,
  "action_proposal_count": 0,
  "official_submission_performed": false,
  "autonomous_action_performed": false,
  "execution_status": "not_executed",
  "pixel_derived_truth_used": false,
  "vss_output_used_as_truth": false,
  "one_truth_packet_audit": "PASS | FAIL",
  "boundary_audit": "PASS | FAIL",
  "forbidden_claims_present": false,
  "tests": {
    "targeted_r8": "PASS | FAIL",
    "full_discovery": "PASS | FAIL",
    "test_count": 0
  },
  "limitations": []
}
```
