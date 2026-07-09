# MAIN-CITYBRAIN-D11-LOCAL-REVIEW-STATE-CONTRACT-R1

Define local review-state contract for selected items. This is not an official workflow engine.

Allowed local states:
- `not_started`
- `in_review`
- `needs_source`
- `hold`
- `abstain`
- `reviewed`
- `exported_locally`

Allowed verbs:
- `open`
- `ask`
- `run_check`
- `generate_brief`
- `add_local_note`
- `mark_needs_source`
- `place_on_hold`
- `abstain`
- `mark_reviewed`
- `export_local_summary`

Forbidden verbs/action semantics:
- dispatch, route, control, enforce, approve, notify, alert, create case, create ticket, assign official owner, escalate as official workflow, certify finding.

Contract requirements:
- Every state transition is local, logged, and reversible except local export history.
- `abstain` is first-class and requires a plain reason.
- No state transition mints an ID that resembles a city case/ticket/work-order number.
- Export filename may use a local slug/timestamp but must include `LOCAL_REVIEW_ONLY`.

Deliverables:
- `LOCAL_REVIEW_STATE_CONTRACT.json`
- `LOCAL_REVIEW_VERB_CONTRACT.json`
- `FORBIDDEN_VERB_NEGATIVE_TESTS.json`
## Non-negotiable boundary

Do not claim production readiness, public API readiness, live monitoring, operational alerts, autonomous action, dispatch, routing/control, enforcement, official case/ticket creation, legal/certified finding, certified affected asset/building, certified physical geometry, identity/biometric inference, or action execution.

All verbs are review-local only unless this prompt explicitly says otherwise. Local notes/exports/session summaries are not official city records and must not mint IDs that could be mistaken for official case/ticket numbers.
