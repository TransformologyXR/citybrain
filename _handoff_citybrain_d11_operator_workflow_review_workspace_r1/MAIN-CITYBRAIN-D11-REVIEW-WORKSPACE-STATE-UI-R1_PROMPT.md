# MAIN-CITYBRAIN-D11-REVIEW-WORKSPACE-STATE-UI-R1

Add the D11 state layer to the operator cockpit.

Do not rewrite D10 selected-item content. Add state controls and display only:
- current local state
- local note count
- needs-source / hold / abstain / reviewed indicators
- a clear statement that these are local review states only

UI requirements:
- State controls sit beside selected item, not above city facts.
- `abstain` is visible as a valid choice, not hidden in a menu.
- Hold/needs-source must explain why the item is blocked.
- Mark reviewed must not suggest closure, resolution, dispatch, case completion, or official action.
- State badges use plain language: `Needs source`, `On hold`, `Abstained`, `Reviewed locally`.

DOM/text gates:
- No visible official case/ticket/work-order language except in boundary/refusal text.
- No visible raw implementation IDs in the state panel.

Deliverables:
- `REVIEW_WORKSPACE_STATE_UI_REPORT.json`
- Updated cockpit DOM snapshot and default visible text export.
## Non-negotiable boundary

Do not claim production readiness, public API readiness, live monitoring, operational alerts, autonomous action, dispatch, routing/control, enforcement, official case/ticket creation, legal/certified finding, certified affected asset/building, certified physical geometry, identity/biometric inference, or action execution.

All verbs are review-local only unless this prompt explicitly says otherwise. Local notes/exports/session summaries are not official city records and must not mint IDs that could be mistaken for official case/ticket numbers.
