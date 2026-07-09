# SPEC — MAIN-CITYBRAIN-METROPOLIS-VSS-RUNTIME-CONFIGURED-RERUN-R6B

## Objective

Configure a real VSS runtime command or endpoint and rerun the connectivity gate so the Metropolis/VSS lane can move from guarded partial to a verified runtime-ready state.

## Why this exists

R3, R4, and R5 correctly refused to fabricate VSS narration when no runtime was configured. R6 correctly isolated the real blocker: no `--vss-command`, `--vss-endpoint`, `CITYBRAIN_VSS_COMMAND`, or `CITYBRAIN_VSS_ENDPOINT`.

R6B must answer only:

```text
Is a real VSS runtime configured and safely reachable from the CityBrain runner environment?
```

## In scope

- Read explicit VSS runtime configuration from CLI or environment.
- Redact sensitive config fields in artifacts.
- Probe command or endpoint with a bounded timeout.
- Emit a configuration report.
- Emit a connectivity probe report.
- Preserve R5/R6 input lineage.
- Preserve R2 DeepStream candidate observations/events as the current sensor-inferred evidence context.
- Produce a freeze package with audits and hash manifest.

## Out of scope

- No VSS narration generation requirement.
- No media/image/frame upload requirement.
- No candidate event modification.
- No VSS-derived detections, counts, timestamps, locations, identities, or legal conclusions.
- No official record/ticket/case.
- No alert, dispatch, routing, enforcement, or automated action.
- No secret/token disclosure.

## PASS criteria

`PASS_METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6B` is allowed only if:

1. A real VSS runtime command or endpoint is configured.
2. The runner attempts a bounded connectivity probe.
3. The probe executes successfully.
4. Runtime configuration is redacted in all user-facing artifacts.
5. Source-class separation remains intact:
   - DeepStream / Metropolis = `sensor_inferred`
   - VSS = `model_generated_narrative`, and only in later narration tasks
6. No candidate event is modified by the probe.
7. All audits pass.

## Honest partial statuses

Use partial, not fail, when the implementation is correct but runtime is unavailable:

- `PARTIAL_METROPOLIS_VSS_RUNTIME_NOT_CONFIGURED_R6B_CONNECTIVITY_CONTRACT_READY`
- `PARTIAL_METROPOLIS_VSS_RUNTIME_CONFIGURED_BUT_UNREACHABLE_R6B`
- `PARTIAL_METROPOLIS_VSS_RUNTIME_CONFIGURED_BUT_TIMED_OUT_R6B`
- `PARTIAL_METROPOLIS_VSS_RUNTIME_CONFIGURED_BUT_UNSUPPORTED_PROTOCOL_R6B`

## Failure statuses

Use fail when the implementation violates safety or evidence boundaries:

- `FAIL_METROPOLIS_VSS_RUNTIME_CONFIGURATION_SECRET_OR_BOUNDARY_RISK_R6B`
- `FAIL_METROPOLIS_VSS_RUNTIME_PROBE_OVERCLAIMED_R6B`
- `FAIL_METROPOLIS_VSS_RUNTIME_MUTATED_CANDIDATE_EVENT_R6B`
- `FAIL_METROPOLIS_VSS_SOURCE_CLASS_SEPARATION_RISK_R6B`
