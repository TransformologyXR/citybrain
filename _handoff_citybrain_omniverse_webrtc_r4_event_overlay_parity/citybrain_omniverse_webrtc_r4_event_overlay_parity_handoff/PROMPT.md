# PROMPT — MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R4-EVENT-OVERLAY-PARITY

You are implementing:

`MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R4-EVENT-OVERLAY-PARITY`

## Context

The Omniverse/WebRTC lane has already proven:

- native Kit spatial cockpit UI
- live GUI visual acceptance
- local/dev WebRTC browser stream
- WebUI packet panel over the stream
- WebUI camera navigation controls into Kit
- packet-backed selection/focus messaging groundwork
- R3 should prove actual scene prim selection parity

R4 must now prove event overlay parity.

## Product goal

Create a bounded local/replay event overlay path where the same CityBrain event packets drive both:

1. Omniverse Kit overlay markers / prim metadata
2. WebUI event overlay panel / inspector

The WebRTC stream is visual context only. Packets remain the source of truth.

## Required implementation

Create a new runner:

`scripts/run_main_citybrain_omniverse_webrtc_r4_event_overlay_parity.py`

Create output root:

`outputs/main_citybrain_omniverse_webrtc_r4_event_overlay_parity`

## Required source additions or updates

Add only what is needed to prove R4:

- Kit-side event overlay manager or extension hook
- WebUI event overlay/inspector component
- event packet fixtures
- bidirectional event selection/focus message handlers
- event parity audit utilities
- package runner and tests

Prefer reusing existing R2/R3 WebRTC and selection parity code.

## Event packet fixtures

Include at least three event fixtures:

1. `event:replay:blockage:001`
   - active/replay blockage marker
   - target prim or canonical entity
   - evidence refs
   - limitation refs
   - review state `needs_review`
   - no-action state `not_executed`

2. `event:replay:evidence:001`
   - evidence pin / source-linked event marker
   - target prim or canonical entity
   - citations/provenance
   - no-action state

3. `event:replay:limitation:001`
   - limitation/review-only marker
   - cannot-claim text
   - no-action state

Use Barcelona/NYC real scene prims if available. If not, use the R3 primitive corridor scene and record the limitation honestly.

## Required message types

Define or reuse message names such as:

- `citybrain.event.focus_request`
- `citybrain.event.selection_changed`
- `citybrain.event.overlay_upsert`
- `citybrain.event.overlay_clear`

Each message must include:

- message type
- event id
- canonical entity id or prim path
- packet hash/parity token
- evidence refs
- limitation refs
- review state
- no-action state

## Required audits

Produce:

- `EVENT_OVERLAY_PARITY_AUDIT.json`
- `WEB_TO_KIT_EVENT_MESSAGE_CAPTURE.json`
- `KIT_TO_WEB_EVENT_MESSAGE_CAPTURE.json`
- `KIT_EVENT_OVERLAY_REGISTRY.json`
- `WEBUI_EVENT_OVERLAY_STATE.json`
- `ONE_TRUTH_PACKET_AUDIT.json`
- `BOUNDARY_AUDIT.json`
- `STREAM_CONTEXT_REPORT.json`
- `TEST_LOG.txt`
- `HASH_MANIFEST.txt`

## Required tests

Add:

`tests/test_omniverse_webrtc_r4_event_overlay_parity.py`

Test at minimum:

1. Event packet fixtures validate.
2. Web-to-Kit event focus messages preserve packet fields.
3. Kit-to-Web event selection messages preserve packet fields.
4. Event overlay parity audit passes for all fixtures.
5. Boundary audit blocks forbidden claims.
6. Pixel-derived truth remains false.

Run:

- `python -m unittest tests.test_omniverse_spatial_cockpit`
- `python -m unittest tests.test_omniverse_webrtc_r2_selection_parity`
- `python -m unittest tests.test_omniverse_webrtc_r4_event_overlay_parity`
- `.\.venv\Scripts\python.exe -m unittest discover tests`

## Decision logic

Return:

`PASS_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_PARITY_WITH_LIMITATIONS`

only if:

- at least three event overlays are packet-backed
- WebUI -> Kit event selection/focus is captured
- Kit -> WebUI event selection/change is captured
- event packet parity passes
- one-truth packet audit passes
- boundary audit passes
- tests pass
- hash manifest verifies

Return partial if only one side is implemented or if real scene binding is unavailable.

Return fail if packet truth is bypassed, pixels are used as truth, or boundaries regress.

## Package

Zip output root as:

`citybrain_omniverse_webrtc_r4_event_overlay_parity.zip`

Return:

- final status
- output root
- zip path
- event fixture count
- Web-to-Kit capture summary
- Kit-to-Web capture summary
- parity audit summary
- screenshot/recording count if any
- tests summary
- limitations summary
- hash manifest summary
