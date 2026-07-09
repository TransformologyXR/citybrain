# PROMPT — MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R5-REAL-SCENE-OBJECT-EVENT-REVIEW-LOOP

You are implementing `MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R5-REAL-SCENE-OBJECT-EVENT-REVIEW-LOOP`.

## Goal

Create a bounded local/dev Omniverse + WebRTC + WebUI operator loop using real Barcelona and/or NYC USD scene content, actual selectable scene prims, and packet-backed event overlays.

Do not build another stream smoke. The stream already works. This task must prove real scene object/event review behavior.

## Inputs

Use the existing CityBrain repo and prior lane outputs if present:

- Native Kit cockpit R1/R2
- WebRTC bridge R1
- WebRTC R2 bidirectional packet/message parity
- WebRTC R3 scene prim selection parity
- WebRTC R4 event overlay parity
- Barcelona/NYC USD scene assets available in the repo
- Existing CityBrain packet shapes:
  - `EntitySelection`
  - `EvidenceBundle`
  - `AnswerPacket` / subject-answer
  - `CheckReport`
  - `Limitations`
  - `ReviewState`
  - `NoActionState`

Before relying on R3/R4, inspect their decision files and, if available, verify their output packages.

## Implement

Create a new runner:

```text
scripts/run_main_citybrain_omniverse_webrtc_r5_real_scene_object_event_review_loop.py
```

Create output root:

```text
outputs/main_citybrain_omniverse_webrtc_r5_real_scene_object_event_review_loop
```

## Required implementation behavior

1. Load or reference a real Barcelona and/or NYC USD scene.
2. Bind at least 5 actual scene prims to CityBrain packets:
   - at least 2 building/building-like prims
   - at least 1 road/corridor/lane/public-realm prim
   - at least 1 evidence marker or source pin
   - at least 1 event marker or review marker
3. Create or reuse at least 3 replay event overlays.
4. Implement Kit object selection handling:
   - actual Kit prim selection emits `citybrain.selection.changed`
   - WebUI inspector updates from packet fields
5. Implement WebUI object focus/select:
   - WebUI emits `citybrain.selection.focus_request`
   - Kit selects/focuses the actual prim
6. Implement event overlay interaction:
   - WebUI event select focuses/selects Kit marker
   - Kit event marker select updates WebUI event inspector
7. Preserve packet truth:
   - do not infer entity truth from pixels
   - do not infer event truth from pixels
8. Preserve no-action boundary:
   - all events/reviews are `review_only`
   - `NoActionState.status = not_executed`
   - no dispatch/control/enforcement/legal/autonomous claim

## Required reports

Write:

```text
ENTRY_PROMPT.md
README.md
DECISION.json
SCENE_SOURCE_REPORT.json
REAL_SCENE_PRIM_BINDING_AUDIT.json
OBJECT_SELECTION_PARITY_AUDIT.json
EVENT_OVERLAY_PARITY_AUDIT.json
OBJECT_EVENT_RELATIONSHIP_AUDIT.json
WEBUI_DOM_EVIDENCE_REPORT.json
BROWSER_STREAM_EVIDENCE_REPORT.json
ONE_TRUTH_PACKET_AUDIT.json
BOUNDARY_AUDIT.json
TEST_LOG.txt
LIMITATIONS.md
HASH_MANIFEST.txt
```

Suggested folders:

```text
fixtures/
message_captures/
stream_evidence/
webui_evidence/
source_refs/
```

## Required tests

Add tests such as:

```text
tests/test_omniverse_webrtc_r5_real_scene_object_event_review_loop.py
```

Run:

```text
python -m unittest tests.test_omniverse_webrtc_r5_real_scene_object_event_review_loop
python -m unittest discover tests
```

Also run relevant existing regressions for Kit UI, WebRTC R2, R3, and R4.

## Decision logic

Use:

```text
PASS_OMNIVERSE_WEBRTC_R5_REAL_SCENE_OBJECT_EVENT_REVIEW_LOOP_WITH_LIMITATIONS
```

only if real scene prims, object selection parity, event overlay parity, packet audits, boundary audit, tests, and manifest all pass.

Use partial labels honestly if:

- no live browser evidence
- primitive scene only
- object selection works but event-object links are deferred
- WebUI object focus works but Kit-originated selection is not proven
- screenshots exist but browser/DOM/message evidence is incomplete

Fail if:

- pixel-derived truth is used
- object/event parity regresses
- forbidden claims appear
- packet truth is bypassed
