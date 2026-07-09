# PACKAGE CONTRACT — R8

Expected output root:

```text
outputs/main_citybrain_metropolis_vss_narration_evidence_join_r8
```

Expected files:

```text
README.md
R2_R7_INPUT_LINEAGE_SUMMARY_R8.json
NARRATION_EVIDENCE_JOIN_R8.json
EVIDENCE_BUNDLE_JOINED_R8.json
HUMAN_REVIEW_PACKET_R8.json
SOURCE_CLASS_SEPARATION_AUDIT_R8.json
PROSE_VS_DETECTION_CONFLICT_AUDIT_R8.json
CHECK_SOURCE_DEPTH_R8.json
CLAIM_BOUNDARY_AUDIT_R8.json
NO_ACTION_AUDIT_R8.json
SECRET_AUDIT_R8.json
R8_JSON_PARSE_REPORT.json
R8_CLOSEOUT_DECISION.json
HASH_MANIFEST.json
METROPOLIS_VSS_NARRATION_EVIDENCE_JOIN_R8_PACKAGE.zip
```

The joined evidence bundle must preserve separate sections for:

```text
sensor_inferred:
  R2 DeepStream/Metropolis object metadata and candidate observations

model_generated_narrative:
  R7 Spark VSS narration sidecar
```

No package may include secrets, API keys, raw tokens, `.env` files with credentials, or full unredacted HTTP authorization headers.
