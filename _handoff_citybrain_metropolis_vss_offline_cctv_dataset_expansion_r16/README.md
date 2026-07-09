# CityBrain Metropolis/VSS Offline CCTV Dataset Expansion R16 — Handoff

Task:

```text
MAIN-CITYBRAIN-METROPOLIS-VSS-OFFLINE-CCTV-DATASET-EXPANSION-R16
```

R16 adds a license-safe traffic/CCTV-like offline dataset for stronger replay testing, without claiming production live CCTV.

Primary recommendation:
- Use **BMD-45** first because it is fixed-camera/CCTV traffic imagery and the Hugging Face source lists `cc-by-4.0`.
- Treat BMD-45 as **frame replay**, not continuous video.
- Keep AI City CityFlowV2/WTS as a stronger video candidate only after license review.
