# CityBrain Metropolis/VSS — BMD-45 DeepStream Frame Replay Comparison R17

This handoff defines the next bounded sprint after R16:

```text
MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-DEEPSTREAM-FRAME-REPLAY-COMPARISON-R17
```

R16 selected BMD-45 as a license-gated CCTV-like frame replay source and produced dataset-annotation fixtures. R17 asks Codex to fetch or reuse the R16 external image references, run/prepare DeepStream frame replay on `txr-4070`, export actual DeepStream metadata, and compare those `sensor_inferred` detections against the R16 `dataset_annotation` fixtures.

R17 is not a live CCTV task. It is not a production monitoring task. It is not a violation/finding/action task.
