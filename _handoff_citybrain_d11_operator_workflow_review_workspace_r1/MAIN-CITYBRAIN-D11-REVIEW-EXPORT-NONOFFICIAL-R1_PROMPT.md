# MAIN-CITYBRAIN-D11-REVIEW-EXPORT-NONOFFICIAL-R1

Create local export of review packet/session summary.

Export rules:
- File-only local export under outputs.
- Filename must include `LOCAL_REVIEW_ONLY`.
- Header must state that this is not an official ticket/case/finding/action.
- Must include selected item, source records, knowns, unknowns, cannot-claim, checks, local notes, local state, session summary, and citations/provenance references.
- Must not include official ID-looking value except source record IDs already present.

Deliverables:
- `LOCAL_REVIEW_EXPORT_SPEC.json`
- sample local export `.md` and `.json`
- `NONOFFICIAL_EXPORT_AUDIT.json`
## Non-negotiable boundary

Do not claim production readiness, public API readiness, live monitoring, operational alerts, autonomous action, dispatch, routing/control, enforcement, official case/ticket creation, legal/certified finding, certified affected asset/building, certified physical geometry, identity/biometric inference, or action execution.

All verbs are review-local only unless this prompt explicitly says otherwise. Local notes/exports/session summaries are not official city records and must not mint IDs that could be mistaken for official case/ticket numbers.
