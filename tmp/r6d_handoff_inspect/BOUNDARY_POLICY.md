# BOUNDARY POLICY — MAIN-CITYBRAIN-METROPOLIS-VSS-SPARK-SPLIT-HOST-READINESS-R6D

The Metropolis/VSS media lane may output:

- candidate observation
- candidate event
- model confidence
- frame/clip reference
- timestamp/frame/location/camera provenance where available
- uncertainty and false-positive notes
- human-review requirement
- VSS model-generated narration, once configured and guarded

The lane may not output:

- confirmed violation
- legal or certified finding
- identity or biometric inference
- official case/ticket
- dispatch/routing/control/enforcement
- operational alert as command
- automated action

Source separation is mandatory:

```text
DeepStream / Metropolis structured detections = sensor_inferred
VSS natural-language output = model_generated_narrative
Official records = official_record
```

VSS is never a sensor and never a fact source.
