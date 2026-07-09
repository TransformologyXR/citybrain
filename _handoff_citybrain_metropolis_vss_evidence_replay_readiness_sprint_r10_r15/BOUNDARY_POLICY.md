# Boundary Policy — R10–R15

## Allowed outputs

- candidate observation
- candidate event
- model confidence
- frame/clip reference
- timestamp/frame reference
- camera/source provenance
- media hash
- uncertainty notes
- false-positive notes
- VSS narration sidecar as review context
- human-review packet

## Forbidden outputs

- confirmed violation
- legal/certified finding
- identity or biometric inference
- official case/ticket
- dispatch/routing/control/enforcement
- alert as operational command
- automated action
- production monitoring claim
- VSS as a fact source

## Source classes

```text
DeepStream / Metropolis = sensor_inferred
Spark VSS = model_generated_narrative
offline replay source = media_source / replay_source
external annotation = dataset_annotation, not official_record
```
