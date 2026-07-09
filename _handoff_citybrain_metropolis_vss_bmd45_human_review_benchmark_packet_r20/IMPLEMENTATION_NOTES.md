# IMPLEMENTATION NOTES — R20

Use R19 as the source of truth.

Recommended review packet shape:

```json
{
  "packet_id": "...",
  "source_task": "R19",
  "summary": {},
  "source_classes": {},
  "benchmark_scorecard": {},
  "frame_cards": [],
  "review_lists": {
    "false_positive_candidates": [],
    "missed_annotations": []
  },
  "limitations": [],
  "human_review_required": true
}
```

Per-frame card should include:

- frame replay id
- external media ref
- dataset annotation count
- sensor-inferred candidate count
- IoU match counts
- confidence band summary
- review priority
- limitations

Do not create a frontend component in this task unless the repo already has a clear fixture location. A JSON fixture is sufficient for R20 PASS.
