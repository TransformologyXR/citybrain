# Boundary Policy R22

R22 remains candidate-review-only.

Allowed:
- Display review tile/card fixtures.
- Show source class labels.
- Show confidence/IoU/review metrics.
- Link external media refs.
- Preserve human-review packet structure.
- Mark limitations and review-only status.

Forbidden:
- live CCTV claim;
- production monitoring claim;
- official finding;
- legal/certified finding;
- ticket/case creation;
- dispatch/control/action;
- identity or biometric inference;
- treating dataset annotations as official truth;
- treating DeepStream detections as findings;
- treating VSS narration as a fact source.
