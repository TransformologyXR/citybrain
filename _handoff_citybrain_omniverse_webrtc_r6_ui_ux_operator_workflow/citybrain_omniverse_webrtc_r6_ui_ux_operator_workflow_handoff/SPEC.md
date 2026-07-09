# SPEC — MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R6-UI-UX-OPERATOR-WORKFLOW-POLISH

## Objective

Improve the R5 Omniverse/WebRTC cockpit from functional proof to an operator-usable review interface.

## Scope

R6 covers:

1. Side rail / collapsible overlay.
2. Better inspector layout.
3. Authored scene visual polish.
4. Local operator workflow states.
5. Review note and local export UX.
6. Regression and boundary audit.

## Product rule

```text
stream = visual context
packets = truth
operator state = local review state
actions = not_executed
```

## Required UI behavior

### Layout

- Stream remains the primary visual canvas.
- Packet inspector moves into a side rail or collapsible panel.
- Overlay can be minimized.
- Panel state persists during selection changes.
- Object/event controls remain usable.

### Inspector

Inspector must show:

- selected object/event summary
- canonical entity or event ID
- prim path / marker path where applicable
- evidence refs
- limitations
- does-not-prove text
- review state
- NoActionState
- packet hash/source refs

### Workflow states

Supported local states:

- hold
- needs_source
- reviewed
- abstain
- note_added
- cleared/reset

All states are review-only and local.

### Notes/export

Export must include:

- selected object/event packet
- review state
- note text
- evidence refs
- limitation refs
- does-not-prove / cannot-claim text
- no-action state
- packet hash
- local timestamp
- export hash

## Acceptance criteria

PASS if:

- side rail/collapse works
- inspector layout is clearer and tested
- object/event selection parity from R5 still passes
- event overlay parity from R5 still passes
- review workflow state transitions work locally
- notes can be added
- local export JSON is generated
- optional Markdown export generated if feasible
- no-action boundary is present in UI and export
- boundary audit passes
- full discovery tests pass
- hash manifest verifies

## Expected statuses

- `PASS_OMNIVERSE_WEBRTC_R6_UI_UX_OPERATOR_WORKFLOW_POLISH_WITH_LIMITATIONS`
- `PARTIAL_OMNIVERSE_WEBRTC_R6_UI_POLISH_ONLY_WORKFLOW_DEFERRED`
- `PARTIAL_OMNIVERSE_WEBRTC_R6_WORKFLOW_ONLY_SCENE_POLISH_DEFERRED`
- `FAIL_OMNIVERSE_WEBRTC_R6_SELECTION_OR_EVENT_PARITY_REGRESSION`
- `FAIL_OMNIVERSE_WEBRTC_R6_BOUNDARY_OR_ACTION_CLAIM_REGRESSION`

## Non-goals

R6 does not implement production/public streaming, OKAS/GDN/cloud deployment, auth/RBAC/security, live monitoring, perception/camera AI/video inference, VSS/Metropolis/DeepStream, official case/ticket workflow, dispatch/control/enforcement, legal/certified findings, or automated action.
