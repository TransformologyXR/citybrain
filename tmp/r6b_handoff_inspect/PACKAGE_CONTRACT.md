# PACKAGE CONTRACT

Expected implementation output root:

```text
outputs/main_citybrain_metropolis_vss_runtime_configured_rerun_r6b
```

Expected freeze ZIP:

```text
METROPOLIS_VSS_RUNTIME_CONFIGURED_RERUN_R6B_PACKAGE.zip
```

## Required files

```text
README.md
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
```

## Required ZIP checks

- ZIP integrity PASS.
- All JSON parse cleanly.
- HASH_MANIFEST verifies every packaged file except itself.
- No secrets in package.
- Runtime config is redacted where needed.

## Required evidence preservation

The package must state whether it preserved lineage to:

```text
R2 object metadata export
R3 guarded partial
R4 runtime integration partial
R5 configured smoke partial
R6 configuration/connectivity partial
```

It must not alter the R2 candidate observations or candidate event.
