# MAIN-CITYBRAIN-D8-SOURCE-RECORD-UI-INTEGRATION-PREFLIGHT

## Goal
Verify that the source-record recovery handoff and source bundles exist before touching the web UI.

## Required inputs
- `outputs/main_citybrain_d8_source_record_recovery_certified_state_handoff/SOURCE_RECORD_RECOVERY_CERTIFIED_STATE_HANDOFF_DECISION.json`
- `packages/fixtures/london_mobility_source_records/source_record_bundle.json`
- `packages/fixtures/chicago_similar_case_records/similar_case_source_bundle.json`
- `packages/fixtures/helsinki_visual_entity_pick/source_record_bundle.json`
- `packages/fixtures/source_record_recovery_candidate_bundle/source_record_recovery_candidate_bundle.json`
- existing web app under `apps/web-control-room`

## Required checks
1. Parse all JSON inputs.
2. Confirm final handoff status starts with `PASS_MAIN_CITYBRAIN_D8_SOURCE_RECORD_RECOVERY_CERTIFIED_STATE_HANDOFF`.
3. Confirm counts:
   - London >= 1 source/UI card; expected 10.
   - Chicago >= 1 similar-case source/UI card; expected 5.
   - Helsinki >= 1 semantic building/prim card; expected 12.
4. Confirm none of these source bundles is generated from D8 UI copy.
5. Confirm the source bundles remain read-only inputs for this lane.
6. Confirm known blockers remain:
   - M13 candidate observation source detail may still be absent.
   - M07 explicit forbidden-command source record may still be absent.
   - M08 external review-stop source record may still be absent.

## Outputs
Create `outputs/main_citybrain_d8_source_record_ui_integration_preflight` with:
- `SOURCE_RECORD_UI_INTEGRATION_PREFLIGHT_DECISION.json`
- `SOURCE_BUNDLE_INPUT_INDEX.json`
- `SOURCE_BUNDLE_COUNTS_REPORT.json`
- `DATA_REMAINING_BLOCKERS.json`
- claim/no-action/no-mutation/no-fact-invention/secret/hash audits.

## Status rules
PASS only if all required inputs are found and parse cleanly.
PARTIAL if source-record recovery is green but one or more source bundles is missing.
FAIL on malformed JSON or missing source recovery handoff.
