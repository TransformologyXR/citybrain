# SPEC — MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-INTEGRATION-R4

## Objective

Implement a bounded VSS narration runtime integration gate over the verified R2/R3 evidence context.

R4 must:

1. Load and validate the R3 package.
2. Preserve R2 DeepStream/Metropolis structured detection metadata as the only sensor-inferred candidate fact source.
3. Accept a real VSS runtime through one of:
   - `--vss-command`
   - `--vss-endpoint`
   - `CITYBRAIN_VSS_COMMAND`
   - `CITYBRAIN_VSS_ENDPOINT`
4. Execute VSS only if a real command or endpoint is configured.
5. Capture VSS output into structured narration sidecars with `source_class = model_generated_narrative`.
6. Run guardrails that prove VSS does not add detections, override counts, invent timestamps, identify people/plates/faces, create legal or official claims, or command action.
7. Emit a final decision with honest PASS/PARTIAL/FAIL status.
8. Freeze a validation package with JSON/JSONL parse report and hash manifest.

## Input baseline

R3 closeout status:

```text
PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_BLOCKED_GUARDRAILS_READY
```

R3 blocker:

```text
No --vss-command, --vss-endpoint, CITYBRAIN_VSS_COMMAND, or CITYBRAIN_VSS_ENDPOINT was configured.
```

R2 truth preserved through R3:

```text
media_source = container bundled samples/streams/sample_1080p_h264.mp4
zone = bounded_vehicle_zone_r2
detection_class = vehicle_presence_candidate
class_label = car
structured_detection_source_class = sensor_inferred
candidate_observations = 24
candidate_events = 1
```

## Scope

R4 is intentionally narrow:

```text
one R3 package
one R2 EvidenceBundle
one candidate event
one VSS runtime adapter
one narration sidecar stream
one human-review handoff
```

## Allowed outputs

- VSS narration text as `model_generated_narrative`
- references to R2 candidate observation IDs
- references to R2 candidate event / EvidenceBundle
- uncertainty and false-positive notes
- conflict report comparing VSS prose against R2 metadata
- human-review handoff wording
- CHECK narration sufficiency report

## Forbidden outputs

- confirmed violation
- legal or certified finding
- official case/ticket
- identity, biometric, face, or license-plate recognition
- dispatch, routing, control, enforcement, alert-command, or automated action
- production monitoring claim
- VSS as a sensor, official record, or fact source
- new object detections invented by VSS
- object counts from VSS that override R2 metadata
- wall-clock timestamps not present in R2
- sample video described as live CCTV

## Honest statuses

Allowed final statuses:

```text
PASS_METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_WITH_LIMITATIONS
PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_NOT_CONFIGURED_R4_GUARDRAILS_READY
PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_EXECUTED_NO_USABLE_OUTPUT_R4
PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_TIMEOUT_R4
FAIL_METROPOLIS_VSS_NARRATION_RUNTIME_BOUNDARY_VIOLATION_R4
FAIL_METROPOLIS_VSS_NARRATION_RUNTIME_SOURCE_CLASS_DRIFT_R4
FAIL_METROPOLIS_VSS_NARRATION_RUNTIME_PACKAGE_INVALID_R4
```

PASS requires a real configured runtime to execute and produce at least one usable narration record that passes all guardrails.

If no runtime command/endpoint is configured, R4 must remain partial. Do not fabricate VSS output.
