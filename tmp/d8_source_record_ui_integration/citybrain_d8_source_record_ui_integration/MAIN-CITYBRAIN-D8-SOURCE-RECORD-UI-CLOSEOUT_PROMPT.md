# MAIN-CITYBRAIN-D8-SOURCE-RECORD-UI-CLOSEOUT

## Goal
Close the source-record UI integration lane.

## Required upstreams
- Preflight
- Integrated bundle adapter R1
- Web source-record cards R2
- Moment source-record parity R3
- City fact DOM assertion smoke R4

## Required closeout facts
- source-backed default card count
- city/source record counts by city
- blocker card count
- forbidden fixture label hits in default UI
- external viewer readiness status
- remaining moments blocked by data depth
- Kit runtime status carry-forward

## Outputs
Create `outputs/main_citybrain_d8_source_record_ui_closeout` with:
- `SOURCE_RECORD_UI_CLOSEOUT_DECISION.json`
- `SOURCE_RECORD_UI_CLOSEOUT_REPORT.md`
- `CURRENT_WEB_UI_TRUTH_REGISTER.json`
- `REMAINING_SOURCE_DATA_GAPS_FOR_VIEWER_VALIDATION.json`
- audits and hash manifest.

## Status rules
PASS_WITH_LIMITATIONS if source-backed city records now render in the default UI and remaining gaps are explicit.
PARTIAL if source records exist but UI still cannot render them.
FAIL if fixture IDs remain primary UI content.
