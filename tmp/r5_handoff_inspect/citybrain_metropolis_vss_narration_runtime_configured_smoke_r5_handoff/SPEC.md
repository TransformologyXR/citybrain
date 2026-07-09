# SPEC — MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-CONFIGURED-SMOKE-R5

## Objective

Run a configured VSS narration smoke over the verified R4/R2 evidence context and
produce at most one VSS narration sidecar that is explicitly marked as
`model_generated_narrative`.

R5 exists to prove the runtime integration path:

```text
R2 DeepStream object metadata
→ R3/R4 preserved candidate event and evidence context
→ configured VSS runtime command or endpoint
→ VSS narration sidecar
→ guardrail checks
→ EvidenceBundle narration attachment
→ human-review handoff
```

## Hard truth boundary

DeepStream / Metropolis structured metadata remains the only object-detection
source:

```text
source_class = sensor_inferred
```

VSS prose is only a model-generated narrator/reader:

```text
source_class = model_generated_narrative
```

VSS must not become a fact source and must not modify the candidate event.

## Inputs

Required:

- R4 package:
  `METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_PACKAGE.zip`
- R4 package must validate:
  - JSON parse PASS
  - hash manifest PASS
  - R3 validation PASS
  - R2 candidate observations/events preserved as 24/1
- One runtime configuration path:
  - `--vss-command`
  - `--vss-endpoint`
  - `CITYBRAIN_VSS_COMMAND`
  - `CITYBRAIN_VSS_ENDPOINT`

Optional:

- `--timeout-sec`
- `--max-narration-records`, default `1`
- `--dry-run-label`, for package metadata only; not accepted as runtime proof

## VSS command contract

If using command mode, the command should be a template string that supports:

```text
{input_json}
{output_json}
```

Example shape:

```text
--vss-command "python path/to/vss_client.py --input {input_json} --output {output_json}"
```

The runner must write the VSS input packet to `{input_json}` and expect the command
to write output to `{output_json}`. If stdout contains JSON/prose and output file is
absent, the runner may capture stdout, but it must record that path in the execution
report.

## VSS endpoint contract

If using endpoint mode, the runner should POST the VSS input packet as JSON to the
endpoint and capture:

- HTTP status
- response body
- timeout/error metadata
- redacted endpoint reference

The endpoint URL must be redacted in package outputs.

## PASS status

R5 may return:

```text
PASS_METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_WITH_LIMITATIONS
```

only when all are true:

- runtime command or endpoint was configured
- runtime attempted = true
- runtime executed = true
- at least one VSS response body/stdout/output was captured
- at least one normalized narration sidecar was emitted
- sidecar source class is `model_generated_narrative`
- sidecar references the R2/R4 candidate event but does not modify it
- sidecar includes uncertainty and human-review language
- source separation audit PASS
- prose-vs-detection conflict audit PASS
- no-action audit PASS
- claim-boundary audit PASS
- secret audit PASS
- JSON/JSONL parse PASS
- hash manifest PASS

## Partial statuses

Use:

```text
PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_NOT_CONFIGURED_R5_GUARDRAILS_READY
```

when no runtime command/endpoint is configured.

Use:

```text
PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_EXECUTION_FAILED_R5_GUARDRAILS_READY
```

when configuration exists but runtime fails, times out, or returns unusable output.

Use:

```text
PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_NO_USABLE_PROSE_R5_GUARDRAILS_READY
```

when the runtime executes but emits no usable narration after normalization.

## FAIL statuses

Use:

```text
FAIL_METROPOLIS_VSS_NARRATION_RUNTIME_R5_BOUNDARY_OR_FABRICATION
```

if the package fabricates narration, lets VSS create/modify detections, treats VSS
as fact source, creates official records, takes action, leaks secrets, or emits
identity/legal/confirmed-violation claims.

## Explicit non-goals

R5 must not claim:

- production monitoring
- live CCTV deployment
- confirmed violation
- legal/certified finding
- identity or biometric inference
- official case/ticket
- dispatch/routing/control/enforcement
- operational alert command
- autonomous action
