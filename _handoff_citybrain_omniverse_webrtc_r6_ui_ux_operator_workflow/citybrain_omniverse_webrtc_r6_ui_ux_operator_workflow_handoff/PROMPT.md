# PROMPT — MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R6-UI-UX-OPERATOR-WORKFLOW-POLISH

You are implementing `MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R6-UI-UX-OPERATOR-WORKFLOW-POLISH`.

## Context

R5 is closed:

```text
PASS_OMNIVERSE_WEBRTC_R5_REAL_SCENE_OBJECT_EVENT_REVIEW_LOOP_WITH_LIMITATIONS
```

R5 proved a local/dev WebRTC-streamed, packet-backed real-scene object/event review loop.

R6 should polish the operator experience. Do not expand authority. Do not add production/security/perception scope.

## Create

Runner:

```text
scripts/run_main_citybrain_omniverse_webrtc_r6_ui_ux_operator_workflow_polish.py
```

Output root:

```text
outputs/main_citybrain_omniverse_webrtc_r6_ui_ux_operator_workflow_polish
```

## Implement

### 1. Side rail / collapsible overlay

Update WebUI so the packet inspector is not blocking the stream.

Required:

- side rail or collapsible overlay
- expanded/collapsed state
- object/event selection retained across collapse
- stream remains visible

### 2. Inspector layout

Create clear sections:

- Summary
- Evidence
- Limitations
- Does not prove
- Review state
- No action
- Source refs / packet hash

Add empty selection state.

### 3. Scene polish

Where feasible, improve labels, camera bookmarks, marker placement, clutter reduction, material consistency, and object/event discoverability.

Do not imply official affected asset/building truth.

### 4. Workflow states

Add local review state controls:

- hold
- needs_source
- reviewed
- abstain
- note_added
- clear/reset

Log transitions.

### 5. Notes/export

Add review note input.

Export local review packet as JSON. Markdown export optional.

Export must include no-action/review-only boundary.

### 6. Preserve R5 parity

Do not break:

- Kit → Web object selection
- Web → Kit object focus
- Web → Kit event focus
- Kit → Web event marker selection
- one-truth packet audit
- boundary audit

## Required reports

Write:

```text
ENTRY_PROMPT.md
README.md
DECISION.json
UI_LAYOUT_AUDIT.json
INSPECTOR_LAYOUT_AUDIT.json
SCENE_POLISH_REPORT.json
WORKFLOW_STATE_AUDIT.json
REVIEW_NOTE_EXPORT_AUDIT.json
OBJECT_EVENT_PARITY_REGRESSION.json
ONE_TRUTH_PACKET_AUDIT.json
BOUNDARY_AUDIT.json
WEBUI_DOM_EVIDENCE_REPORT.json
TEST_LOG.txt
LIMITATIONS.md
HASH_MANIFEST.txt
```

Suggested folders:

```text
exports/
webui_evidence/
stream_evidence/
message_captures/
source_refs/
```

## Tests

Add:

```text
tests/test_omniverse_webrtc_r6_ui_ux_operator_workflow_polish.py
```

Run:

```text
python -m unittest tests.test_omniverse_webrtc_r6_ui_ux_operator_workflow_polish
python -m unittest discover tests
```

Also run relevant R5/R4/R3/R2 regression tests.

## Decision

Use:

```text
PASS_OMNIVERSE_WEBRTC_R6_UI_UX_OPERATOR_WORKFLOW_POLISH_WITH_LIMITATIONS
```

only if UI layout, inspector layout, workflow states, note/export, R5 parity regressions, tests, and boundary audit pass.

Use partial honestly if scene polish or workflow is deferred.

Fail if action/official case/control/legal claims appear or R5 parity regresses.
