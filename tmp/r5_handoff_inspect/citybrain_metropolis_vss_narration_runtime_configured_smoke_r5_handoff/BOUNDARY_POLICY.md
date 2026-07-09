# BOUNDARY POLICY — Metropolis/VSS R5

## Allowed outputs

R5 may output:

- candidate observation references
- candidate event references
- model confidence copied from R2 metadata
- frame/time references copied from R2/R4 metadata
- media/source provenance
- uncertainty and false-positive notes
- VSS narration sidecar as `model_generated_narrative`
- human-review handoff
- not-a-finding labels

## Forbidden outputs

R5 may not output:

- confirmed violation
- legal/certified finding
- identity or biometric inference
- official case/ticket
- dispatch/routing/control/enforcement
- alert as operational command
- automated action
- new sensor detections invented by VSS
- modified object counts/classes from VSS prose
- production live-monitoring claim

## Source-class rule

```text
DeepStream/Metropolis structured detections = sensor_inferred
VSS prose = model_generated_narrative
official records = not present in this lane
```

VSS must remain a narrator/reader, not a fact source.
