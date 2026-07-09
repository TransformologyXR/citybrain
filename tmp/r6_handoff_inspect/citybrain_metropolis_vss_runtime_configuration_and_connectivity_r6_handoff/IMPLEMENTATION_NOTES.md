# IMPLEMENTATION NOTES — MAIN-CITYBRAIN-METROPOLIS-VSS-RUNTIME-CONFIGURATION-AND-CONNECTIVITY-R6

## Recommended implementation shape

Use a single Python runner with these phases:

```text
1. parse args/env
2. validate R5 package
3. resolve config mode
4. redact config
5. if no config: emit guarded partial artifacts
6. if configured: run bounded probe
7. write probe report
8. run audits
9. write JSON parse report
10. write hash manifest
11. freeze ZIP
```

## Config precedence

Recommended:

```text
CLI value > env var > absent
```

If both command and endpoint are configured, prefer explicit CLI command first, otherwise endpoint. Record this in `selected_mode_reason`.

## Redaction

Redact any value matching:

```text
token=
api_key=
apikey=
password=
secret=
bearer <...>
authorization:
x-api-key:
```

Do not write raw auth headers to any artifact.

## Timeouts

Default timeout:

```text
20 seconds
```

Never hang indefinitely.

## Endpoint safety

Default should be localhost-only:

```text
127.0.0.1
localhost
::1
```

If a non-local endpoint is explicitly configured, record:

```text
non_local_endpoint_explicitly_configured = true
```

Do not infer that non-local is production-safe.

## After R6

Only after R6 PASS should the lane return to:

```text
MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-SMOKE-R7
```

R7 should consume R6 runtime readiness and R2 candidate evidence.
