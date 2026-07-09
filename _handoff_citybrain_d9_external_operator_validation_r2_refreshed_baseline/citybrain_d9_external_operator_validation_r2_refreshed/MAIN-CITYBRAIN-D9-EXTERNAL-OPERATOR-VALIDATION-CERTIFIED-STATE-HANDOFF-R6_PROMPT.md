# MAIN-CITYBRAIN-D9-EXTERNAL-OPERATOR-VALIDATION-CERTIFIED-STATE-HANDOFF-R6

Produce certified-state handoff for the refreshed external operator validation lane.

Must preserve:
- review-only/no-action boundary.
- DIFF deferred if no snapshot cadence.
- Open ASK contract-only if router implementation has not run.
- operator question corpus status.

Output:
- `EXTERNAL_OPERATOR_VALIDATION_CERTIFIED_STATE_HANDOFF_R6_DECISION.json`
- `CURRENT_EXTERNAL_VALIDATION_STATE.md`
- `READY_NEXT_TRACKS.json`
- `DEFERRED_NOT_CLAIMED_LEDGER.json`
- audits and hash manifest.
