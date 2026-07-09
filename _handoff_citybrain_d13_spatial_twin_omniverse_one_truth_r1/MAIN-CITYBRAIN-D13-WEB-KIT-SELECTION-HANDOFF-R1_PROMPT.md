# MAIN-CITYBRAIN-D13-WEB-KIT-SELECTION-HANDOFF-R1

Implement/prove selection handoff between web cockpit and Kit/spatial view.

Minimum flows:
1. Web selected item -> spatial focus/highlight candidate object or area.
2. Kit picked object -> web selected entity/item panel opens or records the same entity packet.

Both sides must show the same:
- entity id/label
- source records
- unknowns/limitations
- no-action state
- review state if D11 available

Deliverables:
- `WEB_KIT_SELECTION_HANDOFF_CONTRACT.json`
- `WEB_TO_KIT_SELECTION_SMOKE_REPORT.json`
- `KIT_TO_WEB_SELECTION_SMOKE_REPORT.json`
## Non-negotiable boundary

Do not claim production readiness, public API readiness, live monitoring, operational alerts, autonomous action, dispatch, routing/control, enforcement, official case/ticket creation, legal/certified finding, certified affected asset/building, certified physical geometry, identity/biometric inference, or action execution.

All verbs are review-local only unless this prompt explicitly says otherwise. Local notes/exports/session summaries are not official city records and must not mint IDs that could be mistaken for official case/ticket numbers.
