# SPEC — MAIN-CITYBRAIN-METROPOLIS-VSS-RUNTIME-PROVISIONING-AND-CONFIGURATION-R6C

## Objective

Provision and configure a real VSS runtime command or endpoint for the Metropolis/VSS media lane, then prove bounded connectivity without running the full narration smoke.

R6C must answer:

```text
Is there a real VSS runtime available?
How is it configured?
Can it be reached safely?
Is the configuration redacted and reproducible?
Can R7 be opened?
```

## Scope

R6C may:

- read `--vss-endpoint`, `--vss-command`, `CITYBRAIN_VSS_ENDPOINT`, and `CITYBRAIN_VSS_COMMAND`;
- write a redacted runtime configuration report;
- probe `/health`, a configured health path, or a bounded command-level health probe;
- emit connectivity/provisioning evidence;
- produce an R6C decision JSON;
- recommend whether R7 may open.

R6C must not:

- generate VSS narration;
- infer new object detections;
- change the R2 candidate event;
- create official records, tickets, alerts, or actions;
- treat VSS prose as a fact source;
- store secrets in artifacts.

## Required inputs

- R6B package or R6B closeout summary.
- Optional endpoint config:
  - `CITYBRAIN_VSS_ENDPOINT`
  - `CITYBRAIN_VSS_HEALTH_PATH`
  - `CITYBRAIN_VSS_TIMEOUT_SECONDS`
- Optional command config:
  - `CITYBRAIN_VSS_COMMAND`
  - `CITYBRAIN_VSS_TIMEOUT_SECONDS`

## Runtime modes

### Endpoint mode

Accepted when a non-empty endpoint is supplied.

Probe rules:

- redact query strings and obvious tokens in artifacts;
- attempt a bounded HTTP health probe;
- capture status code, content type, latency, and a redacted short excerpt;
- never persist auth secrets.

### Command mode

Accepted when a non-empty command is supplied.

Probe rules:

- run only a bounded health/configuration probe;
- enforce timeout;
- capture exit code and redacted stdout/stderr excerpts;
- never persist tokens or file secrets.

## PASS status

```text
PASS_METROPOLIS_VSS_RUNTIME_PROVISIONED_AND_CONNECTED_R6C
```

Allowed only when:

- runtime configured is true;
- probe attempted is true;
- probe executed is true;
- probe status is SUCCESS;
- secret audit PASS;
- source-class boundary PASS;
- no-action audit PASS;
- R7 readiness is true.

## Partial statuses

```text
PARTIAL_METROPOLIS_VSS_RUNTIME_NOT_CONFIGURED_R6C_PROVISIONING_CONTRACT_READY
PARTIAL_METROPOLIS_VSS_RUNTIME_CONFIGURED_BUT_UNREACHABLE_R6C
PARTIAL_METROPOLIS_VSS_RUNTIME_CONFIGURED_BUT_UNSUPPORTED_RESPONSE_R6C
```

## Fail statuses

```text
FAIL_METROPOLIS_VSS_RUNTIME_CONFIGURATION_SECRET_LEAK_R6C
FAIL_METROPOLIS_VSS_RUNTIME_CONFIGURATION_ACTION_OR_MUTATION_RISK_R6C
FAIL_METROPOLIS_VSS_RUNTIME_CONFIGURATION_BOUNDARY_RISK_R6C
```

## R7 gate

R7 may open only if:

```json
{
  "r7_ready": true,
  "runtime_configured": true,
  "probe_status": "SUCCESS"
}
```
