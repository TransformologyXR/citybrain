# PACKAGE CONTRACT — R4

Expected output root:

```text
outputs/main_citybrain_metropolis_vss_narration_runtime_integration_r4
```

Expected freeze ZIP:

```text
METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_PACKAGE.zip
```

## Required files

```text
README.md
INPUT_R3_PACKAGE_VALIDATION_R4.json
VSS_RUNTIME_ADAPTER_CONFIG_R4.json
VSS_INPUT_PACKET_R4.json
VSS_RUNTIME_EXECUTION_REPORT_R4.json
VSS_NARRATION_SIDECARS_R4.jsonl
VSS_NARRATION_NORMALIZATION_REPORT_R4.json
VSS_NARRATION_GUARDRAIL_REPORT_R4.json
VSS_PROSE_VS_DETECTION_CONFLICT_AUDIT_R4.json
SOURCE_CLASS_SEPARATION_AUDIT_R4.json
CLAIM_BOUNDARY_AUDIT_R4.json
NO_ACTION_AUDIT_R4.json
SECRET_AUDIT_R4.json
CHECK_NARRATION_SUFFICIENCY_REPORT_R4.json
HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R4.json
MEDIA_EVIDENCEBUNDLE_WITH_VSS_NARRATION_R4.json
JSON_PARSE_REPORT_R4.json
HASH_MANIFEST.json
METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_DECISION.json
METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_CLOSEOUT_DECISION.json
```

## Required manifest behavior

`HASH_MANIFEST.json` must include every output file except:

```text
HASH_MANIFEST.json
METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_PACKAGE.zip
```

Each manifest entry must include:

```text
file
bytes
sha256
```

## Required JSONL behavior

If no VSS runtime is configured, `VSS_NARRATION_SIDECARS_R4.jsonl` may be empty, but the final status must be partial.

If VSS runtime executes successfully, `VSS_NARRATION_SIDECARS_R4.jsonl` must contain at least one valid JSONL record and all guardrails must pass for PASS.
