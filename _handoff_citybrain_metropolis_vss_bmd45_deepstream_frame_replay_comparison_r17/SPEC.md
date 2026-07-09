# SPEC — MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-DEEPSTREAM-FRAME-REPLAY-COMPARISON-R17

## Objective

Use the R16 BMD-45 offline CCTV-like frame replay source to test the actual DeepStream/Metropolis detection path on `txr-4070`, then compare exported `sensor_inferred` detections against R16 `dataset_annotation` fixtures.

## Inputs

Primary input package:

```text
outputs/main_citybrain_metropolis_vss_offline_cctv_dataset_expansion_r16/METROPOLIS_VSS_OFFLINE_CCTV_DATASET_EXPANSION_R16_PACKAGE.zip
```

Required R16 artifacts:

```text
OFFLINE_REPLAY_SAMPLE_MANIFEST_R16.json
BMD45_SAMPLE_ANNOTATION_SUBSET_R16.json
CANDIDATE_OBSERVATION_FIXTURE_R16.jsonl
CAMERA_SOURCE_REGISTRY_UPDATE_R16.json
MEDIA_PROVENANCE_R16.json
```

External media refs from R16:

```text
3 BMD-45 validation images, external refs only, not packaged media
```

## Host allocation

```text
txr-4070:
  DeepStream / Metropolis frame replay and metadata export
  source_class = sensor_inferred

Spark / spark-2445:
  VSS / LVS / RT-VLM available from prior sprint, but not required for R17
  source_class = model_generated_narrative only if used for optional review text

txr-3090:
  inactive for this media/perception chain
```

## Required behavior

R17 should:

1. Validate R16 input package, hash manifest, and source-boundary audits.
2. Load R16 external media references and dataset annotation fixtures.
3. Fetch or reuse cached BMD-45 validation images.
4. Prepare a DeepStream-compatible replay source from the frames. Acceptable approaches:
   - image-sequence source if supported;
   - generated local MP4/slideshow from the still frames;
   - one-image-at-a-time DeepStream/GStreamer invocation;
   - bounded fallback that records why DeepStream cannot consume still frames.
5. Run DeepStream/Metropolis on `txr-4070` if feasible.
6. Export actual detection metadata; do **not** synthesize DeepStream detections.
7. Normalize actual detections as `sensor_inferred` candidate observations.
8. Compare `sensor_inferred` detections against `dataset_annotation` fixtures using IoU and class-family mapping.
9. Emit comparison metrics and per-frame match records.
10. Emit a human-review comparison packet.
11. Preserve all no-action/no-finding boundaries.

## PASS / PARTIAL / FAIL

### PASS target

```text
PASS_METROPOLIS_VSS_BMD45_DEEPSTREAM_FRAME_REPLAY_COMPARISON_R17_WITH_LIMITATIONS
```

Allowed when:

- R16 package validation passes.
- BMD-45 frames are available or fetched and SHA verified.
- DeepStream/Metropolis is actually attempted and executed on `txr-4070`.
- Actual DeepStream metadata is exported.
- At least one sensor-inferred detection or explicit zero-detection frame result is emitted from the real run.
- Dataset annotations remain `dataset_annotation`.
- DeepStream detections remain `sensor_inferred`.
- IoU comparison is computed.
- Human-review comparison packet is emitted.
- All audits pass.

### Acceptable partial

```text
PARTIAL_METROPOLIS_VSS_BMD45_FRAME_REPLAY_PREPARED_DEEPSTREAM_EXECUTION_BLOCKED
```

Allowed when:

- R16 package validation passes.
- Frames and annotations are prepared.
- DeepStream-compatible replay input is prepared or attempted.
- DeepStream execution is blocked by source-format/container/runtime constraints.
- No detections are fabricated.
- All boundary audits pass.

### FAIL

```text
FAIL_METROPOLIS_VSS_BMD45_FRAME_REPLAY_BOUNDARY_OR_FABRICATION_RISK
```

Required if:

- Dataset annotations are relabeled as DeepStream/Metropolis detections.
- Fake DeepStream detections are created.
- VSS prose is treated as fact.
- Any finding/ticket/dispatch/action/legal/identity claim is created.
- Secrets are packaged.

## Non-goals

```text
live CCTV integration
RTSP production feed
tracking across cameras
identity/biometric recognition
legal violation detection
official ticket/case creation
automated action/dispatch/control
model accuracy certification
```
