# BOUNDARY POLICY — Metropolis/VSS Sprint Closeout R9

## Allowed

- candidate observation
- candidate event
- model confidence
- frame/time/media reference
- VSS model-generated narration sidecar
- source separation
- uncertainty notes
- human review packet

## Not allowed

- confirmed violation
- legal or certified finding
- identity or biometric inference
- official case or ticket
- dispatch / routing / control / enforcement
- alert as operational command
- automated action
- production monitoring claim

## Source-class rule

```text
DeepStream / Metropolis = sensor_inferred
Spark VSS = model_generated_narrative
```

VSS is never a fact source in this sprint.
