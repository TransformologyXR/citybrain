# IMPLEMENTATION NOTES — MAIN-CITYBRAIN-METROPOLIS-VSS-SPARK-SPLIT-HOST-READINESS-R6D

R6D should be useful before Spark VSS is fully installed.

Recommended implementation details:

1. Add a small config loader that checks CLI first, then environment variables.
2. Redact runtime values in output. Store only presence, mode, hostname class, and sanitized URL host/path summary.
3. Keep the R2 evidence payload small: event ID, observation IDs, class labels, confidence, bbox/frame/time refs, media source ref, evidence bundle ref, and limitation refs.
4. Do not send raw video frames in R6D.
5. Do not ask VSS any legal, identity, enforcement, dispatch, or action questions.
6. Prepare R7 prompt payload but mark it `not_executed` unless readiness passes.

Safe VSS task wording for R7 later:

```text
Describe only what the supplied candidate metadata and media reference suggest for human review.
Do not infer identity, legal status, intent, violation confirmation, or operational action.
Do not add new counts or detections beyond the supplied structured metadata.
```
