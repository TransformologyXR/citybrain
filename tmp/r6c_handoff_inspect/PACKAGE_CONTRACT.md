# PACKAGE CONTRACT — R6C

Expected output root:

```text
outputs/main_citybrain_metropolis_vss_runtime_provisioning_and_configuration_r6c
```

Expected freeze ZIP:

```text
METROPOLIS_VSS_RUNTIME_PROVISIONING_AND_CONFIGURATION_R6C_PACKAGE.zip
```

## Required files

```text
README.md
VSS_RUNTIME_PROVISIONING_R6C.json
VSS_RUNTIME_CONNECTIVITY_PROBE_R6C.json
R7_READINESS_GATE_R6C.json
R6C_CLOSEOUT_DECISION.json
RUNTIME_CONFIGURATION_AUDIT_R6C.json
SOURCE_CLASS_SEPARATION_AUDIT_R6C.json
CLAIM_BOUNDARY_AUDIT_R6C.json
NO_ACTION_AUDIT_R6C.json
SECRET_AUDIT_R6C.json
R6C_JSON_PARSE_REPORT.json
HASH_MANIFEST.json
```

## Optional files

```text
REDACTED_STDOUT_EXCERPT.txt
REDACTED_STDERR_EXCERPT.txt
REDACTED_HTTP_RESPONSE_EXCERPT.txt
INPUT_R6B_VALIDATION_R6C.json
```

## Required freeze checks

- ZIP integrity PASS
- JSON parse PASS
- hash manifest PASS
- secret audit PASS
- no-action audit PASS
- source-class separation PASS
- R7 readiness gate present
