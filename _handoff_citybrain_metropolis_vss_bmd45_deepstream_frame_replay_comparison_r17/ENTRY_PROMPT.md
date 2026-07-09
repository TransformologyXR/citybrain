# ENTRY PROMPT — R17 BMD-45 DeepStream Frame Replay Comparison

You are implementing:

```text
MAIN-CITYBRAIN-METROPOLIS-VSS-BMD45-DEEPSTREAM-FRAME-REPLAY-COMPARISON-R17
```

Create the runner:

```text
scripts/run_main_citybrain_metropolis_vss_bmd45_deepstream_frame_replay_comparison_r17.py
```

Create tests:

```text
tests/test_metropolis_vss_bmd45_deepstream_frame_replay_comparison_r17.py
```

Output root:

```text
outputs/main_citybrain_metropolis_vss_bmd45_deepstream_frame_replay_comparison_r17
```

Freeze ZIP:

```text
METROPOLIS_VSS_BMD45_DEEPSTREAM_FRAME_REPLAY_COMPARISON_R17_PACKAGE.zip
```

## Implementation steps

1. Load and validate the R16 package:
   - `METROPOLIS_VSS_OFFLINE_CCTV_DATASET_EXPANSION_R16_PACKAGE.zip`
   - verify JSON parse and hash manifest;
   - extract or read R16 artifacts in memory.

2. Load R16 external media refs:
   - `OFFLINE_REPLAY_SAMPLE_MANIFEST_R16.json`
   - `MEDIA_PROVENANCE_R16.json`
   - `CANDIDATE_OBSERVATION_FIXTURE_R16.jsonl`

3. Fetch or reuse cached BMD-45 image frames:
   - verify bytes/SHA where available;
   - never package large media unless explicitly requested;
   - list media as `external_media_refs` if not packaged.

4. Prepare DeepStream replay input on `txr-4070`:
   - image sequence, generated local MP4/slideshow, or per-image input;
   - record exact method in `DEEPSTREAM_REPLAY_INPUT_PREP_R17.json`.

5. Execute DeepStream/Metropolis if available:
   - record command/container/image;
   - export raw metadata;
   - normalize actual outputs as `source_class=sensor_inferred`.

6. Compare with R16 dataset annotations:
   - annotations stay `source_class=dataset_annotation`;
   - use class family mapping, not brittle exact class-name equality;
   - compute IoU per frame with thresholds `[0.25, 0.5]`;
   - emit matched/unmatched records.

7. Emit human-review packet:
   - show dataset labels and DeepStream detections separately;
   - include cannot-claim text;
   - no official actions.

8. Run audits:
   - source-class separation;
   - dataset annotation not sensor-inferred;
   - claim boundary;
   - no-action;
   - secret;
   - VSS-not-fact-source;
   - no fabricated detections.

## Required output files

```text
R17_CLOSEOUT_DECISION.json
R16_INPUT_VALIDATION_R17.json
R16_LINEAGE_SUMMARY_R17.json
BMD45_FRAME_FETCH_REPORT_R17.json
DEEPSTREAM_REPLAY_INPUT_PREP_R17.json
DEEPSTREAM_RUNTIME_EXECUTION_R17.json
DEEPSTREAM_RAW_METADATA_R17.jsonl
SENSOR_INFERRED_CANDIDATE_OBSERVATIONS_R17.jsonl
DATASET_ANNOTATION_FIXTURE_R17.jsonl
CLASS_MAPPING_R17.json
IOU_COMPARISON_REPORT_R17.json
FRAME_COMPARISON_RECORDS_R17.jsonl
HUMAN_REVIEW_COMPARISON_PACKET_R17.json
SOURCE_CLASS_SEPARATION_AUDIT_R17.json
DATASET_ANNOTATION_BOUNDARY_AUDIT_R17.json
NO_FABRICATED_DETECTIONS_AUDIT_R17.json
CLAIM_BOUNDARY_AUDIT_R17.json
NO_ACTION_AUDIT_R17.json
SECRET_AUDIT_R17.json
VSS_NOT_FACT_SOURCE_AUDIT_R17.json
KNOWN_LIMITATIONS_R17.md
NEXT_SPRINT_RECOMMENDATIONS_R17.md
R17_JSON_PARSE_REPORT.json
HASH_MANIFEST.json
```

## Core rule

Do not fabricate DeepStream detections. Dataset annotations are not DeepStream outputs. VSS is not a fact source. This is candidate-review-only evidence.
