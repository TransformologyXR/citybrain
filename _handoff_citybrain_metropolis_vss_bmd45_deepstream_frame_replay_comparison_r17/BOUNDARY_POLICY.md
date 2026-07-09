# BOUNDARY POLICY — R17

R17 may output:

- dataset annotation fixture
- sensor-inferred candidate observation from actual DeepStream output
- candidate event/context reference
- IoU comparison
- class-family comparison
- frame replay source manifest
- evidence/review packet
- uncertainty and limitations
- human-review requirement

R17 may not output:

- confirmed vehicle presence in a real city context
- confirmed violation
- legal/certified finding
- official case/ticket
- dispatch/routing/control/enforcement
- identity or biometric inference
- live CCTV claim
- production monitoring claim
- automated action

Source classes:

```text
R16 BMD-45 labels = dataset_annotation
DeepStream/Metropolis actual detections = sensor_inferred
VSS output, if referenced at all = model_generated_narrative
```
