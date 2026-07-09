# MAIN-CITYBRAIN-D11-REAL-OPERATOR-SESSION-IMPORT-GATE-R1

Import real non-builder operator session records only if they exist.

Input folder:
- `inputs/d11_operator_gate_sessions/`

Rules:
- Do not fabricate sessions.
- Internal/builder/demo sessions must be explicitly excluded from score.
- If no valid session exists, return `PENDING_REAL_OPERATOR_SESSIONS` and do not fail the workspace build.
- If sessions exist, score task completion, confusion notes, refusal understanding, no-action understanding, brief comprehension, and spontaneous questions.

Deliverables:
- `D11_OPERATOR_SESSION_IMPORT_REPORT.json`
- `D11_OPERATOR_GATE_SCOREBOARD.json`
- `D11_OPERATOR_CONFUSION_NOTES.md`
## Non-negotiable boundary

Do not claim production readiness, public API readiness, live monitoring, operational alerts, autonomous action, dispatch, routing/control, enforcement, official case/ticket creation, legal/certified finding, certified affected asset/building, certified physical geometry, identity/biometric inference, or action execution.

All verbs are review-local only unless this prompt explicitly says otherwise. Local notes/exports/session summaries are not official city records and must not mint IDs that could be mistaken for official case/ticket numbers.
