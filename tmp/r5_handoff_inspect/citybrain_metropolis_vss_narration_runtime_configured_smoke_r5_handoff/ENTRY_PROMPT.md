# ENTRY PROMPT — MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-CONFIGURED-SMOKE-R5

You are implementing the next bounded Metropolis/VSS media-perception lane task
for CityBrain.

## Task name

```text
MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-CONFIGURED-SMOKE-R5
```

## Starting point

R4 closed as:

```text
PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_NOT_CONFIGURED_R4_GUARDRAILS_READY
```

R4 is accepted as a valid guarded partial. It preserved the R2 DeepStream object
metadata truth:

```text
media_source = container bundled samples/streams/sample_1080p_h264.mp4
zone = bounded_vehicle_zone_r2
class_label = car
detection_class = vehicle_presence_candidate
source_class = sensor_inferred
candidate_observations = 24
candidate_events = 1
```

VSS did not run in R4 because no command or endpoint was configured.

## Implement

Create:

```text
scripts/run_main_citybrain_metropolis_vss_narration_runtime_configured_smoke_r5.py
```

The runner must write outputs under:

```text
outputs/main_citybrain_metropolis_vss_narration_runtime_configured_smoke_r5
```

and create the freeze ZIP:

```text
METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_PACKAGE.zip
```

## Required CLI arguments

Support:

```text
--input-r4-zip
--vss-command
--vss-endpoint
--timeout-sec
--max-narration-records
```

Also support environment fallback:

```text
CITYBRAIN_VSS_COMMAND
CITYBRAIN_VSS_ENDPOINT
```

Do not print or package raw secrets. Redact command/endpoint values in output
artifacts.

## Runtime behavior

1. Validate the input R4 package:
   - ZIP integrity
   - JSON/JSONL parse
   - HASH_MANIFEST verification
   - R4 closeout status is guarded partial
   - R2 candidate observations/events preserved as 24/1
   - R2 structured source_class remains `sensor_inferred`

2. Build `VSS_INPUT_PACKET_R5.json` using only bounded evidence:
   - media ref
   - selected candidate event ref
   - object metadata summary
   - frame/time refs
   - zone
   - class label
   - limitations
   - instruction that VSS must narrate only, not infer new facts

3. Resolve runtime mode:
   - command mode from CLI/env command
   - endpoint mode from CLI/env endpoint
   - not_configured if neither exists

4. If runtime is not configured:
   - do not fabricate output
   - emit empty `VSS_NARRATION_SIDECARS_R5.jsonl`
   - final status must be partial-not-configured

5. If runtime is configured:
   - attempt execution once
   - record attempt/execution status
   - capture stdout/stderr/response safely
   - enforce timeout
   - normalize usable prose into at most one sidecar
   - mark the sidecar `source_class = model_generated_narrative`
   - include human-review stop and not-a-finding labels

6. Run audits:
   - source-class separation
   - prose-vs-detection conflict
   - VSS guardrail
   - claim boundary
   - no action
   - secret audit
   - JSON parse
   - hash manifest

7. Create closeout decision and freeze ZIP.

## Required outputs

At minimum produce:

```text
README.md
INPUT_R4_PACKAGE_VALIDATION_R5.json
VSS_RUNTIME_ADAPTER_CONFIG_R5.json
VSS_INPUT_PACKET_R5.json
VSS_RUNTIME_EXECUTION_REPORT_R5.json
VSS_RAW_RESPONSE_CAPTURE_R5.json
VSS_NARRATION_NORMALIZATION_REPORT_R5.json
VSS_NARRATION_SIDECARS_R5.jsonl
MEDIA_EVIDENCEBUNDLE_WITH_VSS_NARRATION_R5.json
HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R5.json
SOURCE_CLASS_SEPARATION_AUDIT_R5.json
VSS_PROSE_VS_DETECTION_CONFLICT_AUDIT_R5.json
VSS_NARRATION_GUARDRAIL_REPORT_R5.json
CLAIM_BOUNDARY_AUDIT_R5.json
NO_ACTION_AUDIT_R5.json
SECRET_AUDIT_R5.json
CHECK_NARRATION_SUFFICIENCY_REPORT_R5.json
METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_DECISION.json
METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_CLOSEOUT_DECISION.json
JSON_PARSE_REPORT_R5.json
HASH_MANIFEST.json
METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_PACKAGE.zip
```

## Acceptance language

Only use PASS if a real configured runtime executes and usable VSS prose is
normalized. Otherwise use an honest PARTIAL status. Never fabricate narration.
