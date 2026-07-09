# SPEC — MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R4-EVENT-OVERLAY-PARITY

## Objective

Prove that CityBrain event overlays can be represented consistently across Omniverse Kit and the WebUI over the local/dev WebRTC bridge.

The stream remains visual context. CityBrain event packets remain the source of truth.

## Scope

Implement a local/replay-only event overlay parity milestone that shows at least three packet-backed event overlays across Kit and WebUI:

1. Active/replay event marker
2. Evidence-linked event marker
3. Limitation/review-only/no-action marker

Each event overlay must be bound to:

- `event_id`
- `canonical_entity_id` or `target_prim_path`
- event type
- review state
- evidence refs
- limitation refs
- no-action state
- packet hash or equivalent parity token

## Required capabilities

### Kit side

- Create or update Kit overlay prims/markers from event packets.
- Attach event packet metadata to prims or a sidecar registry.
- Selecting an event marker in Kit emits a packet-backed event selection/change message.
- Kit selection updates the WebUI inspector through the existing WebRTC/message bridge.

### WebUI side

- Display event overlay list/card over or beside the stream.
- Selecting a WebUI event focuses/selects the corresponding Kit event marker or affected prim.
- The WebUI inspector shows the same evidence, limitations, review state, and no-action state as the Kit selection.

### Parity

For each event fixture, both directions must be proven:

- WebUI event selected -> Kit focuses/selects event marker or affected prim.
- Kit event marker selected -> WebUI event inspector updates.

## Inputs

Preferred:

- R3 scene prim selection parity output package
- Barcelona or NYC scene prim binding registry
- Existing WebRTC bridge and WebUI packet panel
- Local/replay event fixtures or event fabric output

Fallback allowed:

- R3 primitive corridor scene if real Barcelona/NYC scenes are not ready

If fallback is used, status must remain `WITH_LIMITATIONS` and the limitation must be explicit.

## Acceptance criteria

Pass only if all of the following are true:

1. At least three event overlays are created from CityBrain event packets.
2. Event overlays are visible or represented in Kit.
3. Event overlays are visible or represented in WebUI.
4. WebUI -> Kit event selection/focus is captured and audited.
5. Kit -> WebUI event selection/change is captured and audited.
6. Event packet parity passes for all fixture events.
7. Evidence refs, limitation refs, review state, no-action state, and cannot-claim text match across Kit and WebUI.
8. No pixel-derived truth is used.
9. Boundary audit passes.
10. Tests pass.
11. Hash manifest verifies package contents.

## Expected status labels

- `PASS_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_PARITY_WITH_LIMITATIONS`
- `PARTIAL_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_KIT_ONLY`
- `PARTIAL_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_WEBUI_ONLY`
- `PARTIAL_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_NO_REAL_SCENE`
- `FAIL_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_PACKET_TRUTH_REGRESSION`
- `FAIL_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_BOUNDARY_REGRESSION`
- `FAIL_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_NO_SELECTION_PARITY`

## Boundaries / non-claims

Do not claim:

- production live ingestion
- official live monitoring
- dispatch/control/enforcement
- legal/certified finding
- automated action
- perception/VSS/Metropolis/DeepStream execution
- camera AI/video inference
- measurement-grade geometry
- certified physical twin
- public internet/cloud/OKAS/GDN deployment
- auth/RBAC/latency SLA/security hardening

The event overlays are review-only/local-replay context unless a later milestone proves otherwise.

## Required package evidence

The package must include:

- event fixture packets
- Kit overlay registry or prim metadata export
- WebUI event inspector evidence
- Web-to-Kit event message capture
- Kit-to-Web event message capture
- event parity audit
- one-truth packet audit
- boundary audit
- test log
- hash manifest
- screenshot/recording evidence if available

Screenshot evidence is useful but not sufficient alone. Acceptance depends on packet/message audits.
