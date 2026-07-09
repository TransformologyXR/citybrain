# CROSS-HOST ARTIFACT EXCHANGE CONTRACT — MAIN-CITYBRAIN-METROPOLIS-VSS-SPARK-SPLIT-HOST-READINESS-R6D

R7 should pass only a bounded evidence packet from the `txr-4070` Metropolis output to Spark VSS.

Allowed R2-derived fields:

```text
candidate_event_id
candidate_observation_ids
media_source_ref
frame_refs
time_refs
class_label
confidence
bbox_or_region
zone_id
evidence_bundle_ref
limitation_refs
source_class=sensor_inferred
```

Forbidden in R6D/R7 payloads:

```text
secrets
credentials
raw personal data
identity/biometric instructions
official case/ticket IDs created by this lane
action/dispatch/enforcement commands
legal violation labels as findings
```
