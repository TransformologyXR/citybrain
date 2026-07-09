# ENTRY PROMPT — MAIN-CITYBRAIN-METROPOLIS-VSS-RUNTIME-CONFIGURATION-AND-CONNECTIVITY-R6

You are Codex working in the CityBrain repo.

Implement and run:

```text
scripts/run_main_citybrain_metropolis_vss_runtime_configuration_and_connectivity_r6.py
```

Output to:

```text
outputs/main_citybrain_metropolis_vss_runtime_configuration_and_connectivity_r6
```

Freeze as:

```text
METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_PACKAGE.zip
```

## Task

Build the R6 VSS runtime configuration and connectivity gate.

R5 ended as:

```text
PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_NOT_CONFIGURED_R5_GUARDRAILS_READY
```

because no VSS runtime command or endpoint was configured. Do not repeat a narration dry-run. First prove configuration/connectivity.

## Required CLI

Support:

```bash
python scripts/run_main_citybrain_metropolis_vss_runtime_configuration_and_connectivity_r6.py \
  --input-r5-package <path-to-METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_PACKAGE.zip> \
  --output-root outputs/main_citybrain_metropolis_vss_runtime_configuration_and_connectivity_r6 \
  --vss-command "<optional command>" \
  --vss-endpoint "<optional endpoint>" \
  --vss-timeout-seconds 20 \
  --vss-health-path "/health" \
  --vss-version-path "/version" \
  --allow-localhost-only true
```

Also support env fallback:

```text
CITYBRAIN_VSS_COMMAND
CITYBRAIN_VSS_ENDPOINT
CITYBRAIN_VSS_TIMEOUT_SECONDS
CITYBRAIN_VSS_HEALTH_PATH
CITYBRAIN_VSS_VERSION_PATH
```

## Runtime probe rules

### No config

If no command/endpoint is configured:

- do not attempt VSS
- emit zero narration records
- status must be `PARTIAL_METROPOLIS_VSS_RUNTIME_NOT_CONFIGURED_R6_CONNECTIVITY_CONTRACT_READY`
- still emit all audits and manifests

### Command mode

If `--vss-command` or `CITYBRAIN_VSS_COMMAND` is configured:

- execute a bounded probe only
- prefer adding a safe health/version/help argument only if the configured command contract supports it
- otherwise run the configured command exactly as given, but with timeout and output capture
- redact secrets in stored command/config
- capture return code, latency, stdout/stderr snippets
- do not parse prose into claims

### Endpoint mode

If `--vss-endpoint` or `CITYBRAIN_VSS_ENDPOINT` is configured:

- probe health/version endpoint where possible
- default to localhost-only unless explicitly disabled
- capture HTTP status, latency, body snippet
- redact query params/tokens
- no non-local endpoint unless explicitly configured and recorded

## Required output files

Create at least:

```text
R5_PACKAGE_VALIDATION_R6.json
VSS_RUNTIME_CONFIGURATION_R6.json
VSS_RUNTIME_CONNECTIVITY_PROBE_R6.json
VSS_RUNTIME_READINESS_DECISION_R6.json
SOURCE_CLASS_SEPARATION_AUDIT_R6.json
CLAIM_BOUNDARY_AUDIT_R6.json
NO_ACTION_AUDIT_R6.json
SECRET_AUDIT_R6.json
VSS_CONFIGURATION_GUARDRAIL_REPORT_R6.json
CHECK_RUNTIME_CONNECTIVITY_REPORT_R6.json
JSON_PARSE_REPORT_R6.json
HASH_MANIFEST.json
METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_DECISION.json
METROPOLIS_VSS_RUNTIME_CONFIGURATION_AND_CONNECTIVITY_R6_CLOSEOUT_DECISION.json
```

Optional if useful:

```text
VSS_RUNTIME_STDOUT_SNIPPET_R6.txt
VSS_RUNTIME_STDERR_SNIPPET_R6.txt
VSS_RUNTIME_RESPONSE_SNIPPET_R6.txt
```

## Acceptance

PASS only if a real configured VSS command/endpoint is probed successfully.

If still unconfigured, partial is correct. Do not fake success.
