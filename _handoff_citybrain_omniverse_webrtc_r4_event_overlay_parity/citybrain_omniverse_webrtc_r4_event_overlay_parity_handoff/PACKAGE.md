# PACKAGE — MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R4-EVENT-OVERLAY-PARITY

## Output root

`outputs/main_citybrain_omniverse_webrtc_r4_event_overlay_parity/`

## Zip

`citybrain_omniverse_webrtc_r4_event_overlay_parity.zip`

## Required structure

```text
outputs/main_citybrain_omniverse_webrtc_r4_event_overlay_parity/
├── ENTRY_PROMPT.md
├── README.md
├── DECISION.json
├── ACCEPTANCE_REPORT.json
├── LIMITATIONS.md
├── EVENT_FIXTURE_INDEX.json
├── EVENT_OVERLAY_PARITY_AUDIT.json
├── WEB_TO_KIT_EVENT_MESSAGE_CAPTURE.json
├── KIT_TO_WEB_EVENT_MESSAGE_CAPTURE.json
├── KIT_EVENT_OVERLAY_REGISTRY.json
├── WEBUI_EVENT_OVERLAY_STATE.json
├── ONE_TRUTH_PACKET_AUDIT.json
├── BOUNDARY_AUDIT.json
├── STREAM_CONTEXT_REPORT.json
├── TEST_LOG.txt
├── HASH_MANIFEST.txt
├── fixtures/
│   ├── event_replay_blockage_001.json
│   ├── event_replay_evidence_001.json
│   └── event_replay_limitation_001.json
├── stream_evidence/
│   ├── event_overlay_stream_context.png              # optional but preferred
│   └── browser_event_overlay_metadata.json           # optional but preferred
├── source_refs/
│   ├── kit_event_overlay_manager_source_ref.txt
│   ├── webui_event_overlay_source_ref.txt
│   ├── event_message_bridge_source_ref.txt
│   └── r4_runner_source_ref.txt
└── citybrain_omniverse_webrtc_r4_event_overlay_parity.zip
```

## DECISION.json required fields

```json
{
  "task_id": "MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R4-EVENT-OVERLAY-PARITY",
  "status": "PASS_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_PARITY_WITH_LIMITATIONS",
  "event_fixture_count": 3,
  "kit_overlay_registry_status": "PASS",
  "webui_event_overlay_status": "PASS",
  "web_to_kit_event_message_capture": "PASS",
  "kit_to_web_event_message_capture": "PASS",
  "event_overlay_parity_audit": "PASS",
  "one_truth_packet_audit": "PASS",
  "boundary_audit": "PASS",
  "forbidden_claims_present": false,
  "pixel_derived_truth_used": false,
  "stream_context_status": "AVAILABLE | NOT_REQUIRED | PARTIAL",
  "real_scene_used": true,
  "fallback_scene_used": false,
  "tests": {
    "targeted_kit_ui": "PASS",
    "selection_parity_regression": "PASS",
    "event_overlay_parity": "PASS",
    "full_discovery": "PASS",
    "test_count": 0
  },
  "limitations": [],
  "created_at": "<ISO8601>"
}
```

## Minimum pass evidence

- `DECISION.json`
- `EVENT_FIXTURE_INDEX.json`
- 3 event fixture packets
- `KIT_EVENT_OVERLAY_REGISTRY.json`
- `WEBUI_EVENT_OVERLAY_STATE.json`
- `WEB_TO_KIT_EVENT_MESSAGE_CAPTURE.json`
- `KIT_TO_WEB_EVENT_MESSAGE_CAPTURE.json`
- `EVENT_OVERLAY_PARITY_AUDIT.json = PASS`
- `ONE_TRUTH_PACKET_AUDIT.json = PASS`
- `BOUNDARY_AUDIT.json = PASS`
- `TEST_LOG.txt`
- `HASH_MANIFEST.txt`

## Verification notes

A screenshot is useful, but do not accept the package based on screenshot alone. The decisive proof is packet/message parity and matching event state across Kit and WebUI.
