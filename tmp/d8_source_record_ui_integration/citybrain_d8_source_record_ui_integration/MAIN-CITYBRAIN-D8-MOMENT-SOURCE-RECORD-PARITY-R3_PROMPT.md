# MAIN-CITYBRAIN-D8-MOMENT-SOURCE-RECORD-PARITY-R3

## Goal
Re-score the D8 moments against source-backed UI records, not runtime fixture refs.

## Required parity table
For each moment, produce:
- `moment_id`
- `moment_name`
- `default_ui_panel`
- `source_record_backing`: true/false
- `source_record_count`
- `record_class_counts`
- `blocker_if_any`
- `viewer_ready`: true/false
- `allowed_for_external_viewer_validation`: true/false

## Expected current mapping
- Situation/access context: London source records.
- M02: Chicago similar-case records.
- M10: Helsinki semantic building/prim records, plus London source records where relevant.
- M06: only viewer-ready if option choices include real source evidence values; otherwise partial.
- M13: blocked unless D7 candidate observations have source/time/location/label/summary.
- M07: blocked unless explicit forbidden-command refusal log/source record exists, or classify as runtime guardrail not source-backed.
- M08: blocked/source-partial unless external review-stop source/review record exists.
- M03: only passes if a specific source-backed uncertainty field/link renders; generic "uncertain" language does not count.
- M01: only passes if a real source-backed cascade chain renders.

## Outputs
Create `outputs/main_citybrain_d8_moment_source_record_parity_r3` with:
- `MOMENT_SOURCE_RECORD_PARITY_REPORT.json`
- `EXTERNAL_VIEWER_READINESS_BY_MOMENT.json`
- `SOURCE_RECORD_MOMENT_GAPS.md`
- audits and hash manifest.

## Status rules
PASS_WITH_LIMITATIONS if at least one primary demo path has source-backed cards and all unbacked moments are clearly partial/blockers.
Do not claim 10/10 viewer-ready unless all 10 moments have source-backed or explicitly acceptable source-derived records.
