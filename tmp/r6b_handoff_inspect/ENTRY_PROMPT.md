# ENTRY PROMPT — MAIN-CITYBRAIN-METROPOLIS-VSS-RUNTIME-CONFIGURED-RERUN-R6B

You are working in `C:/Users/hazem/Documents/CityBrain`.

Create or update a runner:

```text
scripts/run_main_citybrain_metropolis_vss_runtime_configured_rerun_r6b.py
```

Output root:

```text
outputs/main_citybrain_metropolis_vss_runtime_configured_rerun_r6b
```

Freeze ZIP:

```text
METROPOLIS_VSS_RUNTIME_CONFIGURED_RERUN_R6B_PACKAGE.zip
```

## Inputs

Use the latest R6 package if available:

```text
outputs/main_citybrain_metropolis_vss_runtime_configuration_and_connectivity_r6/METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_PACKAGE.zip
```

Also preserve lineage back to R5/R4/R3/R2 if those packages are available.

## Required runtime config sources

Support CLI and environment. CLI wins over environment.

```text
--vss-command
--vss-endpoint
--vss-timeout-seconds
--vss-probe-mode
--vss-health-path
--redact-runtime-config
```

Environment fallbacks:

```text
CITYBRAIN_VSS_COMMAND
CITYBRAIN_VSS_ENDPOINT
CITYBRAIN_VSS_TIMEOUT_SECONDS
CITYBRAIN_VSS_PROBE_MODE
CITYBRAIN_VSS_HEALTH_PATH
CITYBRAIN_VSS_REDACT_CONFIG
```

## Probe behavior

### Command mode

If `--vss-command` or `CITYBRAIN_VSS_COMMAND` is set:

1. Treat it as an explicit operator-provided command.
2. Execute with timeout.
3. Capture exit code, stdout/stderr length, and a redacted excerpt.
4. Do not pass secrets or media unless explicitly configured.
5. Do not interpret command output as fact.

### Endpoint mode

If `--vss-endpoint` or `CITYBRAIN_VSS_ENDPOINT` is set:

1. Probe endpoint with a safe request.
2. Prefer health path if configured, e.g. `/health`.
3. Capture HTTP status, latency, response content type, and redacted excerpt.
4. Do not send candidate observations unless a later R7 task asks for narration.
5. Do not interpret endpoint output as fact.

## Required outputs

Create:

```text
R6B_CLOSEOUT_DECISION.json
VSS_RUNTIME_CONFIGURATION_R6B.json
VSS_CONNECTIVITY_PROBE_R6B.json
RUNTIME_CONFIGURATION_AUDIT_R6B.json
SOURCE_CLASS_SEPARATION_AUDIT_R6B.json
CLAIM_BOUNDARY_AUDIT_R6B.json
NO_ACTION_AUDIT_R6B.json
SECRET_AUDIT_R6B.json
INPUT_LINEAGE_R6B.json
R6B_JSON_PARSE_REPORT.json
HASH_MANIFEST.json
README.md
```

Optional if useful:

```text
logs/vss_probe_stdout_excerpt.txt
logs/vss_probe_stderr_excerpt.txt
```

## Required closeout logic

PASS only if a real configured command/endpoint is successfully probed.

If no runtime is configured, close as:

```text
PARTIAL_METROPOLIS_VSS_RUNTIME_NOT_CONFIGURED_R6B_CONNECTIVITY_CONTRACT_READY
```

If configured but unreachable/timed out, close as the relevant partial status.

Never fabricate narration.

Never claim VSS as a fact source.

Never modify R2/R5/R6 candidate events.
