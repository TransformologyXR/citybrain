# MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-R2-PREFLIGHT

Verify prerequisites:
- D9 Ask/Watch/Brief/Check milestone freeze exists and is green with limitations.
- D9 pre-validation hardening milestone freeze exists and is green with limitations.
- Recall hardening closeout exists.
- DIFF readiness closeout exists and is deferred due no comparable source-record snapshots.
- Open ASK Router C0 contract exists and is contract-only.
- External operator session input folder exists or can be created.

Output:
- `EXTERNAL_OPERATOR_VALIDATION_R2_PREFLIGHT_DECISION.json`
- `CURRENT_VALIDATION_BASELINE.json`
- `INPUT_SESSION_FOLDER_STATUS.json`

If missing prerequisites, fail safe.
