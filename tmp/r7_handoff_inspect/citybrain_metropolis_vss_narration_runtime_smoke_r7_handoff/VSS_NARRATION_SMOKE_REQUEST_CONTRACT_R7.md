# VSS NARRATION SMOKE REQUEST CONTRACT — R7

## Request intent

Ask VSS to summarize one bounded sample media context for human review only.

## Minimum context

```json
{
  "task_id": "MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-SMOKE-R7",
  "media_ref": "container bundled samples/streams/sample_1080p_h264.mp4",
  "candidate_event_id": "from R2",
  "detection_class": "vehicle_presence_candidate",
  "source_boundary": {
    "deepstream_metropolis": "sensor_inferred",
    "vss": "model_generated_narrative"
  },
  "forbidden_claims": [
    "confirmed violation",
    "identity",
    "official case",
    "dispatch",
    "enforcement",
    "automated action"
  ]
}
```

## Output normalization

Normalize any VSS output to:

```json
{
  "narration_id": "...",
  "candidate_event_id": "...",
  "source_class": "model_generated_narrative",
  "runtime_host": "spark",
  "model_or_service": "...",
  "summary_text": "...",
  "time_refs": [],
  "uncertainty_notes": [],
  "forbidden_claims_detected": [],
  "candidate_event_mutated": false,
  "human_review_required": true
}
```
