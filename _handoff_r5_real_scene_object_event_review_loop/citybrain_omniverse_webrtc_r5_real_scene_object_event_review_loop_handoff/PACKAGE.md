# PACKAGE — MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R5-REAL-SCENE-OBJECT-EVENT-REVIEW-LOOP

## Output root

```text
outputs/main_citybrain_omniverse_webrtc_r5_real_scene_object_event_review_loop/
```

## ZIP

```text
citybrain_omniverse_webrtc_r5_real_scene_object_event_review_loop.zip
```

## Expected files

```text
outputs/main_citybrain_omniverse_webrtc_r5_real_scene_object_event_review_loop/
├── ENTRY_PROMPT.md
├── README.md
├── DECISION.json
├── SCENE_SOURCE_REPORT.json
├── REAL_SCENE_PRIM_BINDING_AUDIT.json
├── OBJECT_SELECTION_PARITY_AUDIT.json
├── EVENT_OVERLAY_PARITY_AUDIT.json
├── OBJECT_EVENT_RELATIONSHIP_AUDIT.json
├── WEBUI_DOM_EVIDENCE_REPORT.json
├── BROWSER_STREAM_EVIDENCE_REPORT.json
├── ONE_TRUTH_PACKET_AUDIT.json
├── BOUNDARY_AUDIT.json
├── LIMITATIONS.md
├── TEST_LOG.txt
├── HASH_MANIFEST.txt
├── fixtures/
│   ├── scene_prim_bindings.json
│   ├── object_selection_packets.json
│   ├── event_overlay_packets.json
│   └── object_event_relationships.json
├── message_captures/
│   ├── kit_to_web_object_selection.jsonl
│   ├── web_to_kit_object_focus.jsonl
│   ├── web_to_kit_event_focus.jsonl
│   └── kit_to_web_event_selection.jsonl
├── stream_evidence/
│   ├── browser_real_scene_object_event_loop.png
│   └── browser_video_metadata.json
├── webui_evidence/
│   ├── webui_dom_snapshot.html
│   ├── webui_dom_metadata.json
│   └── selected_object_event_fields.json
└── source_refs/
    ├── kit_extension_refs.txt
    ├── webui_refs.txt
    ├── runner_ref.txt
    └── scene_asset_refs.txt
```

## DECISION.json minimum fields

```json
{
  "task_id": "MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R5-REAL-SCENE-OBJECT-EVENT-REVIEW-LOOP",
  "status": "PASS_OMNIVERSE_WEBRTC_R5_REAL_SCENE_OBJECT_EVENT_REVIEW_LOOP_WITH_LIMITATIONS",
  "real_scene_used": true,
  "scene_sources": [],
  "actual_scene_prim_binding_count": 0,
  "event_overlay_count": 0,
  "kit_to_web_object_selection": "PASS | PARTIAL | FAIL",
  "web_to_kit_object_focus": "PASS | PARTIAL | FAIL",
  "web_to_kit_event_focus": "PASS | PARTIAL | FAIL",
  "kit_to_web_event_selection": "PASS | PARTIAL | FAIL",
  "object_event_relationship_audit": "PASS | PARTIAL | FAIL",
  "one_truth_packet_audit": "PASS | FAIL",
  "boundary_audit": "PASS | FAIL",
  "pixel_derived_truth_used": false,
  "stream_visual_context_only": true,
  "events_review_only": true,
  "no_action_state": "not_executed",
  "forbidden_claims_present": false,
  "tests": {
    "targeted_r5": "PASS | FAIL",
    "full_discovery": "PASS | FAIL",
    "test_count": 0
  },
  "limitations": []
}
```

## Minimum pass thresholds

- `actual_scene_prim_binding_count >= 5`
- `event_overlay_count >= 3`
- all four selection/focus directions pass
- object-event relationship audit pass
- one-truth packet audit pass
- boundary audit pass
- full discovery pass
- hash manifest verifies
