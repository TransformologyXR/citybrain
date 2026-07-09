# BOUNDARY POLICY — R7

R7 is a narration smoke, not a monitoring system.

## Allowed

- candidate observation context
- candidate event context
- VSS narrative sidecar
- model-generated summary
- evidence reference
- uncertainty note
- human-review requirement

## Not allowed

- confirmed violation
- legal finding
- official case/ticket
- enforcement recommendation
- dispatch/routing/control action
- operational alert command
- identity/biometric inference
- autonomous action

## Source policy

DeepStream/Metropolis object metadata is `sensor_inferred`.

VSS output is `model_generated_narrative`.

VSS must not be a source of detection truth. VSS may describe or summarize, but it cannot alter
the R2 candidate event or change object counts/classes/confidence.
