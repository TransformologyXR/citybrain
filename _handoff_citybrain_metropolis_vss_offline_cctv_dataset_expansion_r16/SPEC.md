# SPEC — MAIN-CITYBRAIN-METROPOLIS-VSS-OFFLINE-CCTV-DATASET-EXPANSION-R16

## Objective

Add a license-safe traffic/CCTV-like offline dataset to strengthen Metropolis/VSS replay testing.

## Preferred R16 source path

### Primary: BMD-45 frame replay

BMD-45 is the preferred first source because it is CCTV-like, vehicle-focused, and has an explicit `cc-by-4.0` license listing on Hugging Face.

Use it as:

```text
fixed CCTV traffic image dataset
→ bounded sample subset
→ frame-replay media/provenance manifest
→ DeepStream/Metropolis compatibility check
→ candidate observation fixture
→ optional Spark VSS narration smoke later
```

Do not call it continuous CCTV video unless a video source is actually used.

### Secondary: AI City CityFlowV2 / WTS

Use only after license review. It is technically closer to traffic camera video, but the license cannot be assumed broad enough for package redistribution or commercial-style demos.

## Target final status

```text
PASS_METROPOLIS_VSS_OFFLINE_CCTV_DATASET_EXPANSION_R16_WITH_LIMITATIONS
```

Acceptable partial:

```text
PARTIAL_METROPOLIS_VSS_CCTV_IMAGE_REPLAY_READY_VIDEO_DATASET_PENDING
```
