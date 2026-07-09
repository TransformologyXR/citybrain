# PACKAGE CONTRACT — R5 Configured VSS Narration Smoke

## Output root

```text
outputs/main_citybrain_metropolis_vss_narration_runtime_configured_smoke_r5
```

## Freeze ZIP

```text
METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_PACKAGE.zip
```

## Required package files

```text
README.md
INPUT_R4_PACKAGE_VALIDATION_R5.json
VSS_RUNTIME_ADAPTER_CONFIG_R5.json
VSS_INPUT_PACKET_R5.json
VSS_RUNTIME_EXECUTION_REPORT_R5.json
VSS_RAW_RESPONSE_CAPTURE_R5.json
VSS_NARRATION_NORMALIZATION_REPORT_R5.json
VSS_NARRATION_SIDECARS_R5.jsonl
MEDIA_EVIDENCEBUNDLE_WITH_VSS_NARRATION_R5.json
HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R5.json
SOURCE_CLASS_SEPARATION_AUDIT_R5.json
VSS_PROSE_VS_DETECTION_CONFLICT_AUDIT_R5.json
VSS_NARRATION_GUARDRAIL_REPORT_R5.json
CLAIM_BOUNDARY_AUDIT_R5.json
NO_ACTION_AUDIT_R5.json
SECRET_AUDIT_R5.json
CHECK_NARRATION_SUFFICIENCY_REPORT_R5.json
METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_DECISION.json
METROPOLIS_VSS_NARRATION_RUNTIME_CONFIGURED_SMOKE_R5_CLOSEOUT_DECISION.json
JSON_PARSE_REPORT_R5.json
HASH_MANIFEST.json
```

## Required closeout fields

The closeout decision must include:

```text
status
task_name
schema_version
input_r4_package_validation_status
runtime_status
runtime_mode
runtime_configured
vss_runtime_attempted
vss_runtime_executed
vss_narration_records
structured_detection_source_class
vss_output_source_class
vss_is_fact_source
candidate_event_modified_by_vss
human_review_required
no_action_taken
official_record_created
audits
limitations
validation_package_ref
```

## Hash manifest

`HASH_MANIFEST.json` must exclude itself and the freeze ZIP. Every other package
file must be listed with SHA-256 and byte size.
