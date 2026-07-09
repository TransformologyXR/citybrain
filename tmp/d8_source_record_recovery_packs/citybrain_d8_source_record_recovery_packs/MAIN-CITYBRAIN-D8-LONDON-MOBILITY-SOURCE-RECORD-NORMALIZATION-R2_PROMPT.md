# MAIN-CITYBRAIN-D8-LONDON-MOBILITY-SOURCE-RECORD-NORMALIZATION-R2

Goal: normalize raw London source records into human-facing source record cards.

Create `london_mobility_source_records.json` with records shaped as:

{
  "record_id": "...",
  "source_family": "TfL Road Disruption | LFB Incident | LAQN Measurement",
  "source_dataset": "...",
  "source_record_id": "...",
  "city": "London",
  "place_label": "...",
  "street_or_asset": "...",
  "event_or_observation": "...",
  "record_time": "...",
  "viewer_summary": "...",
  "why_it_matters_for_mobility_access": "...",
  "evidence_fields": {...},
  "license_or_attribution": "...",
  "limitations": [...]
}

Hard rule:
Do not invent missing fields. Use DATA_DEPTH_GAP per record when missing.

Outputs:
- LONDON_MOBILITY_SOURCE_RECORDS.json
- LONDON_MOBILITY_DATA_DEPTH_GAPS.json
- LONDON_MOBILITY_NORMALIZATION_REPORT.json
