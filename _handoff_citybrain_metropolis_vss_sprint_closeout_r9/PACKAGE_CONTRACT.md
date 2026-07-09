# PACKAGE CONTRACT — MAIN-CITYBRAIN-METROPOLIS-VSS-SPRINT-CLOSEOUT-R9

## Expected output folder

```text
outputs/main_citybrain_metropolis_vss_sprint_closeout_r9
```

## Expected freeze ZIP

```text
METROPOLIS_VSS_SPRINT_CLOSEOUT_R9_PACKAGE.zip
```

## Required files

```text
SPRINT_CLOSEOUT_DECISION_R9.json
R1_R9_LINEAGE_SUMMARY_R9.json
RUNTIME_HOST_ALLOCATION_FINAL_R9.json
SOURCE_CLASS_SEPARATION_FINAL_AUDIT_R9.json
CLAIM_BOUNDARY_FINAL_AUDIT_R9.json
NO_ACTION_FINAL_AUDIT_R9.json
VSS_NOT_FACT_SOURCE_FINAL_AUDIT_R9.json
HUMAN_REVIEW_HANDOFF_FINAL_R9.json
KNOWN_LIMITATIONS_R9.md
NEXT_SPRINT_RECOMMENDATIONS_R9.md
R9_JSON_PARSE_REPORT.json
HASH_MANIFEST.json
METROPOLIS_VSS_SPRINT_CLOSEOUT_R9_PACKAGE.zip
```

## Optional but useful files

```text
R8_INPUT_VALIDATION_SUMMARY_R9.json
R8_ARTIFACT_INSPECTION_REPORT_R9.json
FINAL_SOURCE_CLASS_MATRIX_R9.json
SECRET_AUDIT_R9.json
README.md
TEST_LOG_R9.txt
```

## Hash manifest rules

- Use SHA-256.
- Include every generated file except `HASH_MANIFEST.json` and the freeze ZIP itself.
- Include byte counts.
- Verify the manifest before writing the closeout decision or include a readback report after zip creation.
