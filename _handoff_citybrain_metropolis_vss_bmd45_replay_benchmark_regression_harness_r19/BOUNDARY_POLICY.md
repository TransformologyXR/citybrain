# BOUNDARY POLICY — R19

R19 is a replay benchmark/regression harness for candidate-review evidence.

Allowed:

- dataset annotation fixtures
- sensor-inferred candidate observations
- IoU comparison
- confidence threshold bands
- drift review packets
- human-review benchmark packets

Forbidden:

- production live CCTV claim
- official finding
- legal/certified conclusion
- ticket/case creation
- dispatch/control/action
- identity or biometric inference
- VSS as fact source
- action thresholds

Every threshold is a review threshold, not an enforcement threshold.
