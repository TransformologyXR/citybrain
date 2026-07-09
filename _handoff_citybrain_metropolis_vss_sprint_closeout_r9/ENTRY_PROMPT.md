# ENTRY PROMPT — MAIN-CITYBRAIN-METROPOLIS-VSS-SPRINT-CLOSEOUT-R9

You are implementing the final Metropolis/VSS sprint closeout package.

## Task

Create:

```text
scripts/run_main_citybrain_metropolis_vss_sprint_closeout_r9.py
```

Output root:

```text
outputs/main_citybrain_metropolis_vss_sprint_closeout_r9
```

Freeze ZIP:

```text
METROPOLIS_VSS_SPRINT_CLOSEOUT_R9_PACKAGE.zip
```

## Inputs

Use the verified R1-R8 artifacts. At minimum, consume:

```text
outputs/main_citybrain_metropolis_vss_narration_evidence_join_r8/METROPOLIS_VSS_NARRATION_EVIDENCE_JOIN_R8_PACKAGE.zip
```

R8 must contain:

- `R8_CLOSEOUT_DECISION.json`
- `R2_R7_INPUT_LINEAGE_SUMMARY_R8.json`
- `NARRATION_EVIDENCE_JOIN_R8.json`
- `EVIDENCE_BUNDLE_JOINED_R8.json`
- `HUMAN_REVIEW_PACKET_R8.json`
- R8 audits
- `HASH_MANIFEST.json`

## Implementation requirements

1. Validate the R8 package:
   - ZIP integrity.
   - JSON parse.
   - hash manifest.
   - final status PASS.
   - R2/R7 lineage preserved.
   - candidate event not mutated.

2. Build the sprint lineage summary:
   - R1 candidate observation contract/camera-health.
   - R2 object metadata export.
   - R3-R6 blocked/guarded partials.
   - R6C provisioning/connectivity.
   - R7 VSS narration runtime smoke.
   - R8 evidence join.

3. Emit final closeout artifacts:
   - `SPRINT_CLOSEOUT_DECISION_R9.json`
   - `R1_R9_LINEAGE_SUMMARY_R9.json`
   - `RUNTIME_HOST_ALLOCATION_FINAL_R9.json`
   - `SOURCE_CLASS_SEPARATION_FINAL_AUDIT_R9.json`
   - `CLAIM_BOUNDARY_FINAL_AUDIT_R9.json`
   - `NO_ACTION_FINAL_AUDIT_R9.json`
   - `VSS_NOT_FACT_SOURCE_FINAL_AUDIT_R9.json`
   - `HUMAN_REVIEW_HANDOFF_FINAL_R9.json`
   - `KNOWN_LIMITATIONS_R9.md`
   - `NEXT_SPRINT_RECOMMENDATIONS_R9.md`
   - `R9_JSON_PARSE_REPORT.json`
   - `HASH_MANIFEST.json`
   - `METROPOLIS_VSS_SPRINT_CLOSEOUT_R9_PACKAGE.zip`

4. Do not rerun DeepStream.
5. Do not rerun Spark VSS.
6. Do not emit new narration.
7. Do not mutate R2/R7/R8 inputs.

## Required final boundary text

Every human-facing summary must include the boundary:

```text
This is candidate review evidence only. DeepStream/Metropolis is sensor-inferred.
Spark VSS is model-generated narrative context only and is not a fact source.
Human review is required. This is not a finding, violation, official case,
ticket, dispatch, enforcement action, identity inference, or automated action.
```

## PASS / PARTIAL / FAIL

PASS:

```text
PASS_METROPOLIS_VSS_MEDIA_CANDIDATE_OBSERVATION_AND_NARRATION_SPRINT_CLOSEOUT_WITH_LIMITATIONS
```

PARTIAL:

```text
PARTIAL_METROPOLIS_VSS_SPRINT_CLOSEOUT_BLOCKED_MISSING_R8_OR_AUDITS
```

FAIL:

```text
FAIL_METROPOLIS_VSS_SPRINT_CLOSEOUT_BOUNDARY_OR_SOURCE_CLASS_VIOLATION
```
