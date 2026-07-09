# BOUNDARY POLICY — R16

Allowed outputs:
- dataset source registry,
- media provenance,
- offline replay sample manifest,
- camera/source registry,
- candidate observations,
- evidence/review packets,
- limitations.

Forbidden outputs:
- production live CCTV claim,
- confirmed violation/finding,
- legal/certified conclusion,
- official ticket/case,
- dispatch/routing/control/enforcement,
- identity or biometric inference,
- autonomous action.

Source-class rules:
- DeepStream/Metropolis detections: `sensor_inferred`
- VSS narration: `model_generated_narrative`
- Dataset annotations: `dataset_annotation`
- Synthetic fixtures: `synthetic_or_replay`
