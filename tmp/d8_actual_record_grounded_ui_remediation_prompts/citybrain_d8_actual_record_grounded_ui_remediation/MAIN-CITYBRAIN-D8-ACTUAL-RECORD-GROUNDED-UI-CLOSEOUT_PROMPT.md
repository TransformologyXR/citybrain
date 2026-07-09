# MAIN-CITYBRAIN-D8-ACTUAL-RECORD-GROUNDED-UI-CLOSEOUT

## Objective

Close the actual-record-grounded UI remediation lane.

## Closeout requirements

Required pass conditions:

- data-depth audit complete
- fact-card model created
- web default view patched to actual records/cards
- generic subsystem narration removed from default panels
- technical IDs hidden by default
- no fact invention audit passes
- moment-to-record parity report complete
- local web launch still passes
- claim/no-action/no-mutation/secret/hash audits pass

If actual record payloads are missing from the runtime bundle, the closeout may pass with limitations only if:

- missing data is explicitly reported in `DATA_DEPTH_GAP_LEDGER.json`
- UI shows data-depth gaps instead of generic filler
- no viewer-ready claim is made for missing categories

## Output artifacts

- `ACTUAL_RECORD_GROUNDED_UI_CLOSEOUT_DECISION.json`
- `ACTUAL_RECORD_GROUNDED_UI_CLOSEOUT_SUMMARY.md`
- `DATA_DEPTH_GAP_LEDGER.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_FACT_INVENTION_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`

