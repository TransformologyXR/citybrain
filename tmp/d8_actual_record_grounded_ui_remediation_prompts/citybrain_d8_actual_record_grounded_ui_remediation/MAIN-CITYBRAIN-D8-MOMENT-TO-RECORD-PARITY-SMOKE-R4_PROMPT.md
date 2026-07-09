# MAIN-CITYBRAIN-D8-MOMENT-TO-RECORD-PARITY-SMOKE-R4

## Objective

Re-run D8 moment parity, but upgrade the standard: a moment only passes if it has a render home backed by at least one actual record/card, not just a generic sentence.

## Required moment checks

For each demonstrable moment, record:

```json
{
  "moment_id": "M02",
  "moment_name": "Cross-city memory",
  "render_home_selector": "#similar-cases",
  "actual_record_card_count": 4,
  "source_record_refs": ["..."],
  "default_view_human_readable": true,
  "technical_ids_hidden_by_default": true,
  "status": "PASS|PARTIAL|FAIL"
}
```

## Moment-specific expectations

- M02 must show actual similar-case records or mark partial.
- M13 must show actual candidate observation records or mark partial.
- M03 must show at least one actual uncertain/qualitative link or mark partial.
- M06 must show actual option cards with actual shared axes/values/statuses or mark partial.
- M07 must show actual forbidden command rejection/log evidence.
- M08 must show actual eligible/non-promotion Track D packets in human terms.
- M10 must show actual entity/relationship/source cards, not subsystem names.
- M01 must show actual cascade/link chain or mark partial.

## Output artifacts

- `MOMENT_TO_ACTUAL_RECORD_PARITY_REPORT.json`
- `MOMENT_TO_ACTUAL_RECORD_PARITY_REPORT.md`
- `UPDATED_DEMONSTRABILITY_SCOREBOARD_AFTER_RECORD_GROUNDING.json`
- `HASH_MANIFEST.json`

