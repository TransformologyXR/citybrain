# MAIN-CITYBRAIN-D13-SPATIAL-PREFLIGHT

Inputs:
- D10 Kit runtime probe result.
- D11 review-state contract.
- D12 handoff if available.
- Current web cockpit/runtime bundle.
- Prior Omniverse/Kit D8/D6 outputs, if present.

Hard blockers:
- Missing/failed Kit runtime probe => `BLOCKED_KIT_RUNTIME_NOT_READY` unless running an explicit environment repair sublane.
- Missing entity/source binding candidates => stop as `BLOCKED_NO_ENTITY_PRIM_BINDING_CANDIDATES`.

Deliverables:
- `D13_SPATIAL_PREFLIGHT_DECISION.json`
- `D13_INPUT_LEDGER.json`
## Non-negotiable boundary

Do not claim production readiness, public API readiness, live monitoring, operational alerts, autonomous action, dispatch, routing/control, enforcement, official case/ticket creation, legal/certified finding, certified affected asset/building, certified physical geometry, identity/biometric inference, or action execution.

All verbs are review-local only unless this prompt explicitly says otherwise. Local notes/exports/session summaries are not official city records and must not mint IDs that could be mistaken for official case/ticket numbers.
