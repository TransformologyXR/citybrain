# ENTRY PROMPT — MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-EVIDENCE-JOIN-R8

You are implementing the next bounded Metropolis/VSS lane step for CityBrain.

## Task

Implement:

```text
scripts/run_main_citybrain_metropolis_vss_narration_evidence_join_r8.py
```

Output to:

```text
outputs/main_citybrain_metropolis_vss_narration_evidence_join_r8
```

Create freeze ZIP:

```text
METROPOLIS_VSS_NARRATION_EVIDENCE_JOIN_R8_PACKAGE.zip
```

## Inputs

Consume the existing verified packages if present:

```text
outputs/main_citybrain_metropolis_vss_object_metadata_export_r2/METROPOLIS_VSS_OBJECT_METADATA_EXPORT_R2_PACKAGE.zip
outputs/main_citybrain_metropolis_vss_narration_runtime_smoke_r7/METROPOLIS_VSS_NARRATION_RUNTIME_SMOKE_R7_PACKAGE.zip
```

The runner may also accept:

```text
--r2-package <path>
--r7-package <path>
--output-root <path>
```

## Required behavior

1. Validate R7 package:
   - JSON parse
   - JSONL parse
   - hash manifest
   - R7 closeout status
   - sidecar count >= 1

2. Validate R2 lineage from R7 and/or R2 package:
   - candidate_event_id
   - candidate_observation_count
   - detection_class
   - source_class=sensor_inferred

3. Read the R7 VSS narration sidecar:
   - source_class must equal `model_generated_narrative`
   - `vss_is_fact_source` must be false
   - `candidate_event_mutated` must be false
   - human review must be required

4. Emit joined outputs:
   - `NARRATION_EVIDENCE_JOIN_R8.json`
   - `EVIDENCE_BUNDLE_JOINED_R8.json`
   - `HUMAN_REVIEW_PACKET_R8.json`
   - `SOURCE_CLASS_SEPARATION_AUDIT_R8.json`
   - `CHECK_SOURCE_DEPTH_R8.json`
   - `NO_ACTION_AUDIT_R8.json`
   - `CLAIM_BOUNDARY_AUDIT_R8.json`
   - `SECRET_AUDIT_R8.json`
   - `R8_CLOSEOUT_DECISION.json`
   - `HASH_MANIFEST.json`
   - `METROPOLIS_VSS_NARRATION_EVIDENCE_JOIN_R8_PACKAGE.zip`

## Hard rule

Do not let VSS prose create, confirm, override, count, certify, or modify facts. VSS can only be an attached narration sidecar for human review context.

## Expected PASS status

```text
PASS_METROPOLIS_VSS_NARRATION_EVIDENCE_JOIN_R8_WITH_LIMITATIONS
```
