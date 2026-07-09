# Known Limitations R19

- R19 is an offline BMD-45 replay benchmark, not production live CCTV.
- BMD-45 annotations are dataset fixtures, not official truth.
- DeepStream detections are sensor-inferred candidate observations only.
- Regression thresholds are review/engineering thresholds, not action thresholds.
- Model outputs may vary by DeepStream version, container version, GPU, configuration, and decode path.
- VSS is not used as a fact source.
