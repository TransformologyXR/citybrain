# PACKAGE — MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R3-SCENE-PRIM-SELECTION-PARITY

## Output root

`outputs/main_citybrain_omniverse_webrtc_r3_scene_prim_selection_parity/`

## ZIP

`citybrain_omniverse_webrtc_r3_scene_prim_selection_parity.zip`

## Required package structure

```text
outputs/main_citybrain_omniverse_webrtc_r3_scene_prim_selection_parity/
├── ENTRY_PROMPT.md
├── README.md
├── DECISION.json
├── LIMITATIONS.md
├── SCENE_PRIM_BINDING_REGISTRY.json
├── KIT_TO_WEB_SELECTION_CAPTURE.json
├── WEB_TO_KIT_SELECTION_CAPTURE.json
├── SELECTION_PARITY_AUDIT.json
├── WEB_DOM_INSPECTOR_EVIDENCE.json
├── KIT_SELECTION_EVIDENCE.json
├── STREAM_CONTEXT_EVIDENCE.json
├── ONE_TRUTH_PACKET_AUDIT.json
├── BOUNDARY_AUDIT.json
├── TEST_LOG.txt
├── HASH_MANIFEST.txt
├── stream_evidence/
│   ├── browser_stream_context.png
│   └── stream_metadata.json
├── browser_dom_evidence/
│   ├── selected_object_inspector.json
│   └── selected_object_dom_snapshot.html
├── kit_selection_evidence/
│   ├── kit_selected_prim_state.json
│   └── kit_spatial_cockpit_visible_text.txt
├── fixtures/
│   ├── entity_selection_packets.json
│   ├── evidence_bundles.json
│   ├── limitations.json
│   ├── review_states.json
│   └── no_action_states.json
└── source_refs/
    ├── modified_files.json
    └── source_ref_summary.md
```

## Required `DECISION.json` fields

```json
{
  "task_id": "MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R3-SCENE-PRIM-SELECTION-PARITY",
  "status": "PASS_OMNIVERSE_WEBRTC_R3_SCENE_PRIM_SELECTION_PARITY_WITH_LIMITATIONS",
  "selected_prim_count": 0,
  "real_scene_used": false,
  "primitive_fallback_used": false,
  "kit_to_web_selection_capture": "PASS | PARTIAL | FAIL",
  "web_to_kit_selection_capture": "PASS | PARTIAL | FAIL",
  "selection_parity_audit": "PASS | PARTIAL | FAIL",
  "web_dom_inspector_evidence": "PASS | PARTIAL | FAIL",
  "kit_selection_evidence": "PASS | PARTIAL | FAIL",
  "one_truth_packet_audit": "PASS | FAIL",
  "boundary_audit": "PASS | FAIL",
  "pixel_derived_truth_used": false,
  "stream_visual_context_only": true,
  "forbidden_claims_present": false,
  "tests": {
    "targeted_r3": "PASS | FAIL",
    "full_discovery": "PASS | FAIL",
    "test_count": 0
  },
  "hash_manifest": {
    "entries": 0,
    "verified": 0,
    "problems": 0
  },
  "limitations": [],
  "created_at": "<ISO8601>"
}
```

## Minimum PASS evidence

- At least 3 selectable prims.
- At least 2 directions captured:
  - Kit-to-Web.
  - Web-to-Kit.
- WebUI inspector evidence.
- Kit selected prim evidence.
- Parity audit.
- One-truth packet audit.
- Boundary audit.
- Stream screenshot/metadata as context only.
- Tests and hash manifest.
