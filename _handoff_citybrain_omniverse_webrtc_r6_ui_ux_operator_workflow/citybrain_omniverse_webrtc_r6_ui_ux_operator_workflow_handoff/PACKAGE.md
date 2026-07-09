# PACKAGE — MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R6-UI-UX-OPERATOR-WORKFLOW-POLISH

## Output root

```text
outputs/main_citybrain_omniverse_webrtc_r6_ui_ux_operator_workflow_polish/
```

## ZIP

```text
citybrain_omniverse_webrtc_r6_ui_ux_operator_workflow_polish.zip
```

## Expected structure

```text
outputs/main_citybrain_omniverse_webrtc_r6_ui_ux_operator_workflow_polish/
├── ENTRY_PROMPT.md
├── README.md
├── DECISION.json
├── UI_LAYOUT_AUDIT.json
├── INSPECTOR_LAYOUT_AUDIT.json
├── SCENE_POLISH_REPORT.json
├── WORKFLOW_STATE_AUDIT.json
├── REVIEW_NOTE_EXPORT_AUDIT.json
├── OBJECT_EVENT_PARITY_REGRESSION.json
├── WEBUI_DOM_EVIDENCE_REPORT.json
├── ONE_TRUTH_PACKET_AUDIT.json
├── BOUNDARY_AUDIT.json
├── LIMITATIONS.md
├── TEST_LOG.txt
├── HASH_MANIFEST.txt
├── exports/
│   ├── review_packet_example.json
│   ├── review_packet_example.md
│   └── export_hashes.json
├── webui_evidence/
│   ├── expanded_side_rail_dom_snapshot.html
│   ├── collapsed_side_rail_dom_snapshot.html
│   ├── selected_object_inspector_fields.json
│   ├── selected_event_inspector_fields.json
│   └── workflow_state_dom_metadata.json
├── stream_evidence/
│   ├── r6_side_rail_expanded.png
│   ├── r6_side_rail_collapsed.png
│   └── r6_scene_polish_context.png
├── message_captures/
│   ├── workflow_state_transitions.jsonl
│   ├── note_export_events.jsonl
│   └── selection_event_regression.jsonl
└── source_refs/
    ├── webui_refs.txt
    ├── kit_refs.txt
    ├── runner_ref.txt
    └── scene_polish_refs.txt
```

## DECISION.json minimum fields

```json
{
  "task_id": "MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R6-UI-UX-OPERATOR-WORKFLOW-POLISH",
  "status": "PASS_OMNIVERSE_WEBRTC_R6_UI_UX_OPERATOR_WORKFLOW_POLISH_WITH_LIMITATIONS",
  "r5_dependency_status": "PASS_OMNIVERSE_WEBRTC_R5_REAL_SCENE_OBJECT_EVENT_REVIEW_LOOP_WITH_LIMITATIONS",
  "side_rail_collapsible_overlay": "PASS | PARTIAL | FAIL",
  "inspector_layout": "PASS | PARTIAL | FAIL",
  "scene_polish": "PASS | PARTIAL | DEFERRED | FAIL",
  "workflow_states": "PASS | PARTIAL | FAIL",
  "review_note_export": "PASS | PARTIAL | FAIL",
  "object_event_parity_regression": "PASS | FAIL",
  "one_truth_packet_audit": "PASS | FAIL",
  "boundary_audit": "PASS | FAIL",
  "pixel_derived_truth_used": false,
  "stream_visual_context_only": true,
  "review_state_local_only": true,
  "no_action_state": "not_executed",
  "forbidden_claims_present": false,
  "tests": {
    "targeted_r6": "PASS | FAIL",
    "full_discovery": "PASS | FAIL",
    "test_count": 0
  },
  "limitations": []
}
```
