# SPEC — MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R5-REAL-SCENE-OBJECT-EVENT-REVIEW-LOOP

## Objective

Move beyond primitive/replay smoke by proving a real city-scene operator loop:

- real Barcelona and/or NYC USD scene content is loaded
- actual scene prims are bound to CityBrain entity packets
- replay event overlays attach to real/candidate scene context
- selecting objects or events in Kit updates the WebUI inspector
- selecting objects or events in WebUI focuses/selects Kit prims/markers
- evidence, limitations, review state, and `not_executed` remain packet-driven

## Starting point

Reported previous milestones:

- R3 scene prim selection parity: reported `PASS_OMNIVERSE_WEBRTC_R3_SCENE_PRIM_SELECTION_PARITY_WITH_LIMITATIONS`
- R4 event overlay parity: reported `PASS_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_PARITY_WITH_LIMITATIONS`

Before using them as dependencies, verify their output ZIPs directly if available.

## Scope

Implement R5 as a bounded local/dev reference loop using existing WebRTC, Kit, WebUI, packet, selection, and event overlay infrastructure.

Minimum scene scope:

- Use one real Barcelona or NYC USD scene, not only the primitive corridor.
- Bind at least 5 actual scene prims:
  - at least 2 building/building-like prims
  - at least 1 road/corridor/lane/public-realm prim
  - at least 1 evidence marker or source pin
  - at least 1 event marker or review marker
- Each bound prim must map to a CityBrain packet with:
  - `canonical_entity_id`
  - `prim_path`
  - `entity_type`
  - `evidence_refs`
  - `limitation_refs`
  - `review_state`
  - `no_action_state`
  - `cannot_claim`
  - `packet_hash`

Minimum event scope:

- At least 3 event packets from R4 or a new R5 replay fixture.
- Each event must have:
  - event ID
  - event type
  - affected/context candidate prim refs
  - evidence refs
  - limitation refs
  - review-only state
  - `not_executed` / no-action state
- Event overlays must be visible in Kit and represented in WebUI.

## Required interactions

### Object path

1. Select actual Kit scene prim.
2. Kit emits `citybrain.selection.changed`.
3. WebUI inspector updates.
4. WebUI displays the same packet-backed identity/evidence/limitations/no-action state.

### Web focus path

1. Select/focus object in WebUI.
2. WebUI emits `citybrain.selection.focus_request`.
3. Kit selects/focuses the actual prim.
4. Kit and WebUI report the same packet hash and packet fields.

### Event path

1. Select event in WebUI.
2. Kit focuses/selects event marker and, where applicable, affected/context candidate prim.
3. Select event marker in Kit.
4. WebUI event inspector updates.
5. Event remains review-only and cannot claim official affected-asset truth.

## Evidence requirements

R5 may not pass on logs alone.

Required:

- Browser/WebUI evidence showing the stream panel and CityBrain inspector/panel context.
- DOM or browser automation metadata proving:
  - WebUI route loaded
  - object panel present
  - event panel present
  - selected object/event fields populated
  - video/stream available if stream is part of the run
- Message capture logs for both directions.
- Packet parity audit.
- Boundary audit.
- Hash manifest.

Screenshots alone are not authoritative. They are supporting visual evidence only.

## Acceptance criteria

PASS only if:

- Real Barcelona/NYC scene content is used or the package clearly identifies the real scene fixture.
- At least 5 actual scene prim bindings are audited.
- At least 3 replay event overlays are audited.
- Kit-to-Web object selection passes.
- Web-to-Kit object focus/select passes.
- Web-to-Kit event focus/select passes.
- Kit-to-Web event marker selection passes.
- Object-event relationship display is bounded as candidate/review context.
- One-truth packet audit passes.
- Boundary audit passes.
- Full regression tests pass.
- Hash manifest verifies.

## Expected statuses

- `PASS_OMNIVERSE_WEBRTC_R5_REAL_SCENE_OBJECT_EVENT_REVIEW_LOOP_WITH_LIMITATIONS`
- `PARTIAL_OMNIVERSE_WEBRTC_R5_REAL_SCENE_BINDING_NO_LIVE_BROWSER_EVIDENCE`
- `PARTIAL_OMNIVERSE_WEBRTC_R5_PRIMITIVE_SCENE_ONLY`
- `PARTIAL_OMNIVERSE_WEBRTC_R5_EVENT_OBJECT_LINKS_DEFERRED`
- `FAIL_OMNIVERSE_WEBRTC_R5_PIXEL_DERIVED_TRUTH_OR_BOUNDARY_REGRESSION`
- `FAIL_OMNIVERSE_WEBRTC_R5_SELECTION_PARITY_REGRESSION`

## Boundaries

Do not claim:

- production/cloud/public WebRTC
- OKAS/GDN deployment
- auth/RBAC/security hardening
- latency/SLA guarantee
- live monitoring
- perception/camera AI/video inference
- Metropolis/VSS/DeepStream
- official affected-building or affected-asset determination
- measurement-grade geometry
- dispatch/control/enforcement
- legal/certified finding
- automated action

Core rule:

```text
stream = visual context
packets = truth
objects/events = candidate/review context
actions = not_executed
```
