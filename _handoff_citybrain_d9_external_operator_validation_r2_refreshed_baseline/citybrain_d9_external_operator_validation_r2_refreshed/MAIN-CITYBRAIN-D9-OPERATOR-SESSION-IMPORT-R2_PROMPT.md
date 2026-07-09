# MAIN-CITYBRAIN-D9-OPERATOR-SESSION-IMPORT-R2

Import completed operator session records from `inputs/d9_external_operator_sessions/`.

Reject:
- README files.
- templates with empty fields.
- internal builder-only records unless explicitly flagged as internal partial.
- generated placeholder records.

Accept:
- completed non-builder operator/reviewer session JSON/CSV/MD with enough responses to score.

Output:
- `OPERATOR_SESSION_IMPORT_REPORT.json`
- `USABLE_OPERATOR_SESSIONS.json`
- `REJECTED_SESSION_FILES.json`

If no usable sessions, status must be `PARTIAL_PENDING_OPERATOR_SESSION_RECORDS`.
