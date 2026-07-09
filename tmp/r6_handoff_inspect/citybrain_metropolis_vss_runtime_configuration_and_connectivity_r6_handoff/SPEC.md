# SPEC — MAIN-CITYBRAIN-METROPOLIS-VSS-RUNTIME-CONFIGURATION-AND-CONNECTIVITY-R6

## Objective

Build a bounded VSS runtime configuration and connectivity gate that determines whether CityBrain can actually invoke a VSS runtime through either:

```text
--vss-command
--vss-endpoint
CITYBRAIN_VSS_COMMAND
CITYBRAIN_VSS_ENDPOINT
```

R6 should not attempt to prove narration quality. It should prove runtime availability, connectivity, invocation contract, safe capture, timeout handling, and secret redaction.

## Why this task exists

R3, R4, and R5 correctly refused to fabricate VSS narration. R4 and R5 remained partial because no VSS command or endpoint was configured. R6 isolates that blocker.

## Required inputs

At minimum:

```text
METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_PACKAGE.zip
```

Optional runtime config:

```text
--vss-command "<command string>"
--vss-endpoint "http://127.0.0.1:<port>/<path>"
--vss-timeout-seconds <int>
--vss-health-path <path>
--vss-version-path <path>
--allow-localhost-only true
```

Equivalent env vars:

```text
CITYBRAIN_VSS_COMMAND
CITYBRAIN_VSS_ENDPOINT
CITYBRAIN_VSS_TIMEOUT_SECONDS
CITYBRAIN_VSS_HEALTH_PATH
CITYBRAIN_VSS_VERSION_PATH
```

## Scope

R6 must:

1. Validate the input R5 package.
2. Read VSS runtime config from CLI/env.
3. Redact secrets before writing any config artifact.
4. Classify runtime mode:
   - `not_configured`
   - `command`
   - `endpoint`
   - `both_configured_prefer_cli`
5. If not configured, stop with guarded partial.
6. If configured, run a bounded connectivity probe:
   - command mode: `--version`, `--help`, or configured health command if available
   - endpoint mode: health/version GET probe, localhost-preferred
7. Record:
   - attempted/executed
   - command or endpoint used, redacted
   - timeout
   - return code or HTTP status
   - stdout/stderr snippets or response body snippet
   - latency
   - connectivity status
8. Emit a runtime readiness decision.
9. Preserve all prior source-class and no-action boundaries.
10. Freeze a package with manifests and audits.

## Out of scope

R6 must not:

- claim VSS narration passed
- fabricate VSS prose
- modify R2 candidate events
- create new detections
- create new candidate observations
- infer identities
- confirm violations or findings
- create official records, tickets, alerts, dispatches, routes, enforcement actions, or control commands
- call external non-local endpoints unless explicitly configured and recorded
- log secrets or bearer/API tokens

## PASS status

Use:

```text
PASS_METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_WITH_LIMITATIONS
```

Only if:

- a real command or endpoint is configured,
- runtime connectivity probe is attempted and executed,
- probe succeeds within timeout,
- safe runtime metadata is captured,
- secrets are redacted,
- no-action/source-class/claim-boundary audits pass.

## Partial statuses

Use:

```text
PARTIAL_METROPOLIS_VSS_RUNTIME_NOT_CONFIGURED_R6_CONNECTIVITY_CONTRACT_READY
```

if no VSS command or endpoint is configured.

Use:

```text
PARTIAL_METROPOLIS_VSS_RUNTIME_CONFIGURED_CONNECTIVITY_FAILED_R6
```

if a command/endpoint is configured but the probe fails, times out, or returns an unusable response while guardrails remain intact.

## Fail statuses

Use:

```text
FAIL_METROPOLIS_VSS_RUNTIME_CONFIGURATION_BOUNDARY_BREACH_R6
```

if the run logs secrets, fabricates narration, modifies candidate events, creates action/official records, or treats VSS as sensor truth.
