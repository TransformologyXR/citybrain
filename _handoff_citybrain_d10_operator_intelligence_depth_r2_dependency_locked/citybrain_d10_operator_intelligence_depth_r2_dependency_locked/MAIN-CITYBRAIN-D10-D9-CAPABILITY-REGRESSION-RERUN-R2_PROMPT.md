# MAIN-CITYBRAIN-D10-D9-CAPABILITY-REGRESSION-RERUN-R2

## Purpose
Run the standing D9 capability regression gate after D10 surface/content changes.

This gate must recur at every closeout D10–D13.

## Required checks
- Held-out ASK still works at prior level.
- Out-of-scope/refusal path still refuses cleanly.
- Non-story BRIEF still generates.
- Mode-run stamping / DOM attributes preserved.
- No-action boundary still visible and technically true.
- Operator visible text does not expose implementation internals.
- No mutation/secret/claim boundary audits pass.

## Output
`D9_CAPABILITY_REGRESSION_RERUN_R2_REPORT.json`

## Hard fail
A smarter D10 cockpit that regresses D9 core capabilities cannot freeze.
