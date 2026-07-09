# MAIN-CITYBRAIN-D8-SOURCE-RECORD-UI-MILESTONE-FREEZE

## Goal
Freeze a source-record-backed web UI baseline for the next capture/viewer sprint.

## Required
- Closeout PASS or PASS_WITH_LIMITATIONS.
- Default UI renders real/source-derived city records.
- Technical IDs collapsed by default.
- Data-depth blockers explicit for missing M13/M07/M08 or any other missing source fact.
- External viewer validation readiness recomputed from moment/source parity.
- Hash/no-mutation/no-action/no-fact-invention/secret audits pass.

## Freeze semantics
This is a validation baseline for maintained app source, not permanent immutability. Future remediation may edit `apps/web-control-room`, but this freeze records the baseline used for capture/viewer validation.

## Outputs
Create `outputs/main_citybrain_d8_source_record_ui_milestone_freeze` with:
- `SOURCE_RECORD_UI_MILESTONE_FREEZE_DECISION.json`
- `SOURCE_RECORD_UI_BASELINE_SUMMARY.md`
- `SOURCE_RECORD_UI_VALIDATION_PACKAGE.zip`
- `EXTERNAL_VIEWER_GO_NO_GO.json`
- audits and hash manifest.

## Status rules
PASS_WITH_LIMITATIONS if a source-record-backed web UI baseline is frozen.
PARTIAL if source records are not yet consumable by UI.
FAIL on fact invention, fixture-label leakage in default content, or boundary violation.
