# VSS SPARK ENDPOINT CONTRACT — MAIN-CITYBRAIN-METROPOLIS-VSS-SPARK-SPLIT-HOST-READINESS-R6D

Endpoint mode must accept a bounded JSON request and return bounded JSON.

Request shape:

```json
{
  "request_id": "string",
  "task": "candidate_observation_narration_for_human_review",
  "source_class": "model_generated_narrative_request",
  "structured_evidence_ref": "string",
  "candidate_event": { },
  "candidate_observations": [],
  "limitations": []
}
```

Response shape:

```json
{
  "request_id": "string",
  "runtime_status": "SUCCESS|ERROR",
  "source_class": "model_generated_narrative",
  "narration": "string",
  "claims_added": [],
  "guardrail_flags": [],
  "candidate_event_modified": false
}
```

The endpoint must not return secrets or official/action claims.
