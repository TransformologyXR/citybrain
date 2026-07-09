# SPEC — MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R3-SCENE-PRIM-SELECTION-PARITY

## Objective

Promote the WebRTC/Kit/WebUI lane from streamed visual context + packet panel controls into **real scene-prim interaction parity**.

The next milestone must prove that actual Omniverse Kit scene objects/prim paths are selectable and focusable through the CityBrain WebUI/Kit bridge:

- Selecting a scene object in Kit updates the WebUI inspector.
- Selecting/focusing an object in WebUI selects/focuses the corresponding Kit prim.
- Both sides resolve to the same CityBrain packet-backed entity/evidence/limitations/no-action truth.
- Stream pixels remain visual context only; packets remain authority.

## Current accepted context

Completed/accepted so far:

1. Native Kit Spatial Cockpit UI R1/R2 reached live GUI evidence.
2. Local/dev WebRTC stream to browser is working.
3. WebUI packet panel exists over the stream.
4. WebUI controls can send camera/navigation messages into Kit.
5. Browser stream shows a primitive corridor scene, and mouse navigation works manually.
6. Bidirectional message parity groundwork exists, but the next product step is **actual scene object selection parity**, not more fixture-only message parity.

## Scope

Implement R3 against a real or semi-real USD scene if available, prioritizing Barcelona/NYC building/corridor assets over primitive fixtures.

Minimum scene entities:

- At least 3 selectable Kit prims.
- At least 1 building or building-like prim.
- At least 1 corridor/road/lane or infrastructure prim.
- At least 1 evidence/limitation/review marker prim.
- Every selected prim must map to a CityBrain canonical entity packet or a bounded candidate packet.

Required interaction paths:

1. **Kit → WebUI**
   - User selects a Kit scene prim.
   - Kit emits `citybrain.selection.changed`.
   - WebUI receives and updates selected entity inspector.
   - WebUI shows entity ID, prim path, evidence refs, limitations, review state, no-action state, and cannot-claim text.

2. **WebUI → Kit**
   - User clicks/focuses/selects an entity in WebUI.
   - WebUI emits `citybrain.selection.focus_request`.
   - Kit selects the mapped prim path and focuses/framing camera where supported.
   - Kit Spatial Cockpit updates to the same packet-backed selection.

3. **Parity**
   - Same canonical entity ID.
   - Same prim path.
   - Same evidence refs.
   - Same limitation refs.
   - Same review state.
   - Same no-action/not-executed state.
   - Same cannot-claim text.
   - Same packet hash or equivalent deterministic parity hash.

## Inputs

Use existing project assets where available:

- R2 WebRTC/browser stream bridge.
- R2 bidirectional selection/message parity implementation.
- Native Kit Spatial Cockpit panel.
- Selection inspector.
- Overlay manager.
- WebUI stream panel and packet selection panel.
- Barcelona/NYC real building USD scenes if already available.
- Primitive corridor scene only as fallback.

## Required outputs

Create output root:

`outputs/main_citybrain_omniverse_webrtc_r3_scene_prim_selection_parity/`

Required artifacts:

- `ENTRY_PROMPT.md`
- `DECISION.json`
- `README.md`
- `LIMITATIONS.md`
- `SCENE_PRIM_BINDING_REGISTRY.json`
- `KIT_TO_WEB_SELECTION_CAPTURE.json`
- `WEB_TO_KIT_SELECTION_CAPTURE.json`
- `SELECTION_PARITY_AUDIT.json`
- `WEB_DOM_INSPECTOR_EVIDENCE.json`
- `KIT_SELECTION_EVIDENCE.json`
- `STREAM_CONTEXT_EVIDENCE.json`
- `ONE_TRUTH_PACKET_AUDIT.json`
- `BOUNDARY_AUDIT.json`
- `TEST_LOG.txt`
- `HASH_MANIFEST.txt`
- `stream_evidence/`
- `browser_dom_evidence/`
- `kit_selection_evidence/`
- `fixtures/`

Package ZIP:

`citybrain_omniverse_webrtc_r3_scene_prim_selection_parity.zip`

## Acceptance criteria

### PASS

Use status:

`PASS_OMNIVERSE_WEBRTC_R3_SCENE_PRIM_SELECTION_PARITY_WITH_LIMITATIONS`

Only if all are true:

1. WebRTC live stream is available as visual context.
2. At least 3 scene prims are selectable/focusable.
3. Kit-to-Web selection is captured from actual scene prim selection, not only synthetic fixture messages.
4. Web-to-Kit selection/focus is captured and applies to actual Kit prim path(s).
5. WebUI inspector updates from actual selected object packet.
6. Kit Spatial Cockpit updates to same selected object packet.
7. `SELECTION_PARITY_AUDIT.json` passes for all selected prims.
8. `ONE_TRUTH_PACKET_AUDIT.json` passes.
9. `BOUNDARY_AUDIT.json` passes.
10. Tests pass.
11. Hash manifest verifies.

### PARTIAL

Use one of:

- `PARTIAL_OMNIVERSE_WEBRTC_R3_SCENE_PRIM_SELECTION_WEB_TO_KIT_ONLY`
- `PARTIAL_OMNIVERSE_WEBRTC_R3_SCENE_PRIM_SELECTION_KIT_TO_WEB_ONLY`
- `PARTIAL_OMNIVERSE_WEBRTC_R3_SCENE_PRIM_SELECTION_FIXTURE_ONLY_NO_ACTUAL_PRIM`
- `PARTIAL_OMNIVERSE_WEBRTC_R3_REAL_SCENE_UNAVAILABLE_PRIMITIVE_FALLBACK_ONLY`

### FAIL

Use one of:

- `FAIL_OMNIVERSE_WEBRTC_R3_PIXEL_DERIVED_TRUTH_USED`
- `FAIL_OMNIVERSE_WEBRTC_R3_ONE_TRUTH_REGRESSION`
- `FAIL_OMNIVERSE_WEBRTC_R3_BOUNDARY_REGRESSION`
- `FAIL_OMNIVERSE_WEBRTC_R3_NO_INTERACTABLE_SCENE_PRIMS`

## Boundaries

Do not claim:

- production streaming
- OKAS/GDN/cloud deployment
- public internet readiness
- auth/RBAC/security hardening
- latency SLA
- live monitoring
- dispatch/control/enforcement
- legal/certified findings
- automated action
- camera AI/video inference
- Metropolis/VSS/DeepStream execution
- certified twin
- measurement-grade geometry
- official affected building/asset

Stream pixels are visual context only. Packet truth remains authoritative.

## Follow-on: MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R4-EVENT-OVERLAY-PARITY

After R3 passes, implement event overlays:

- active/replay event marker appears in Kit scene
- same event appears in WebUI event panel
- selecting event marker updates both inspectors
- event packet contains evidence, limitations, review state, no-action state
- no live monitoring claim unless the event fabric is truly live and governed
