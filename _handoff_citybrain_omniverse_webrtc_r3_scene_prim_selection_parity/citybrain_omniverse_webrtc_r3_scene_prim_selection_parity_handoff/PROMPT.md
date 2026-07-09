# PROMPT — MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R3-SCENE-PRIM-SELECTION-PARITY

You are implementing:

`MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R3-SCENE-PRIM-SELECTION-PARITY`

## Mission

The WebRTC stream works and WebUI camera/navigation controls work. Now implement **actual scene prim selection parity**.

Do not build another screenshot-only or fixture-only demo. The milestone must prove real scene objects in Omniverse Kit can participate in the CityBrain packet loop.

## Current project context

Already available:

- Native Kit Spatial Cockpit panel.
- Selection inspector.
- Overlay manager.
- Local/dev WebRTC browser stream.
- WebUI packet panel over stream.
- WebUI-to-Kit camera navigation messages.
- Bidirectional message parity groundwork.
- Primitive corridor smoke scene.
- Real Barcelona/NYC building USD assets may exist and should be preferred.

## Implementation requirements

### 1. Scene prim binding registry

Create or extend a registry that maps Kit prim paths to CityBrain selection packets.

Each binding must include:

- `prim_path`
- `canonical_entity_id`
- `entity_type`
- `display_label`
- `scene_source`
- `evidence_refs`
- `limitation_refs`
- `review_state`
- `no_action_state`
- `cannot_claim`
- `packet_hash`
- `binding_status`
- `selection_enabled`

Prefer real Barcelona/NYC building/corridor scene prims. Use primitive fallback only if real scenes are unavailable, and mark the decision honestly.

### 2. Kit selection listener

When a user selects a Kit prim:

- resolve selected `prim_path`
- look up binding registry
- build `citybrain.selection.changed`
- send to WebUI/message bridge
- update native Kit Spatial Cockpit selection inspector
- preserve limitations/no-action/cannot-claim state

### 3. WebUI focus/select action

When a user selects/focuses an entity in WebUI:

- send `citybrain.selection.focus_request`
- include canonical entity ID, prim path, packet hash, evidence refs, limitation refs
- Kit receives it
- Kit selects the prim path
- Kit frames/focuses it if available
- Kit Spatial Cockpit updates to same packet

### 4. WebUI inspector

WebUI must display the current selected object using packet truth:

- canonical entity ID
- entity label/type
- prim path
- evidence refs
- limitations
- review state
- no-action/not-executed state
- cannot-claim text
- packet hash

Do not infer truth from stream pixels.

### 5. Evidence capture

Produce artifacts that prove both directions:

- `KIT_TO_WEB_SELECTION_CAPTURE.json`
- `WEB_TO_KIT_SELECTION_CAPTURE.json`
- `SELECTION_PARITY_AUDIT.json`
- `WEB_DOM_INSPECTOR_EVIDENCE.json`
- `KIT_SELECTION_EVIDENCE.json`
- stream screenshot or recording as context only

### 6. Tests

Add tests without weakening existing ones.

Suggested tests:

- `tests.test_omniverse_webrtc_r3_scene_prim_selection_parity`
- binding registry schema test
- Kit-to-Web selection packet test
- Web-to-Kit focus request packet test
- parity audit test
- no pixel-derived truth test
- boundary audit test
- regression: R2 parity package still passes

Run:

- targeted R3 tests
- previous Omniverse Kit tests
- previous WebRTC bridge/parity tests
- full test discovery

## Decision rules

### PASS

`PASS_OMNIVERSE_WEBRTC_R3_SCENE_PRIM_SELECTION_PARITY_WITH_LIMITATIONS`

Use only if:

- actual scene prim selection is captured in both directions
- WebUI inspector and Kit inspector show the same packet-backed entity
- parity audit passes
- one-truth audit passes
- boundary audit passes
- tests pass
- hash manifest verifies

### PARTIAL

Use if one direction or actual scene interaction is missing:

- `PARTIAL_OMNIVERSE_WEBRTC_R3_SCENE_PRIM_SELECTION_WEB_TO_KIT_ONLY`
- `PARTIAL_OMNIVERSE_WEBRTC_R3_SCENE_PRIM_SELECTION_KIT_TO_WEB_ONLY`
- `PARTIAL_OMNIVERSE_WEBRTC_R3_SCENE_PRIM_SELECTION_FIXTURE_ONLY_NO_ACTUAL_PRIM`
- `PARTIAL_OMNIVERSE_WEBRTC_R3_REAL_SCENE_UNAVAILABLE_PRIMITIVE_FALLBACK_ONLY`

### FAIL

Use if truth or safety boundaries regress:

- `FAIL_OMNIVERSE_WEBRTC_R3_PIXEL_DERIVED_TRUTH_USED`
- `FAIL_OMNIVERSE_WEBRTC_R3_ONE_TRUTH_REGRESSION`
- `FAIL_OMNIVERSE_WEBRTC_R3_BOUNDARY_REGRESSION`
- `FAIL_OMNIVERSE_WEBRTC_R3_NO_INTERACTABLE_SCENE_PRIMS`

## Output

Create:

`outputs/main_citybrain_omniverse_webrtc_r3_scene_prim_selection_parity/`

Zip:

`citybrain_omniverse_webrtc_r3_scene_prim_selection_parity.zip`

Return:

- final status
- output root
- ZIP path
- selected prim count
- real scene vs primitive fallback
- Kit-to-Web result
- Web-to-Kit result
- parity audit result
- one-truth audit result
- boundary audit result
- test summary
- hash manifest summary
- limitations

## Non-negotiable

Do not claim official/certified/live/actionable city truth. This remains review-only, local/dev, packet-grounded, and no-action.
