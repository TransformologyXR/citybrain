# IMPLEMENTATION NOTES

## Recommended CLI examples

Endpoint mode:

```powershell
python scripts/run_main_citybrain_metropolis_vss_runtime_configured_rerun_r6b.py `
  --vss-endpoint http://127.0.0.1:8000 `
  --vss-health-path /health `
  --vss-timeout-seconds 10 `
  --redact-runtime-config true
```

Command mode:

```powershell
python scripts/run_main_citybrain_metropolis_vss_runtime_configured_rerun_r6b.py `
  --vss-command "python path/to/vss_health_probe.py" `
  --vss-timeout-seconds 20 `
  --redact-runtime-config true
```

Environment mode:

```powershell
$env:CITYBRAIN_VSS_ENDPOINT="http://127.0.0.1:8000"
$env:CITYBRAIN_VSS_HEALTH_PATH="/health"
$env:CITYBRAIN_VSS_TIMEOUT_SECONDS="10"
python scripts/run_main_citybrain_metropolis_vss_runtime_configured_rerun_r6b.py
```

## Redaction guidance

Redact query parameters and headers that may contain tokens.
Redact env var values containing:

```text
KEY
TOKEN
SECRET
PASSWORD
AUTH
BEARER
COOKIE
```

## Probe guidance

Do not send full candidate metadata to VSS in R6B. The purpose is connectivity only.
A later R7 narration smoke may send bounded R2 evidence context after R6B proves runtime availability.
