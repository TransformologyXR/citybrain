# PACKAGE CONTRACT — R16

Expected final ZIP:

```text
METROPOLIS_VSS_OFFLINE_CCTV_DATASET_EXPANSION_R16_PACKAGE.zip
```

Required files:

```text
R16_CLOSEOUT_DECISION.json
OFFLINE_DATASET_SOURCE_REGISTRY_R16.json
DATASET_LICENSE_REVIEW_R16.json
OFFLINE_REPLAY_SAMPLE_MANIFEST_R16.json
CAMERA_SOURCE_REGISTRY_UPDATE_R16.json
MEDIA_PROVENANCE_R16.json
CANDIDATE_OBSERVATION_FIXTURE_R16.jsonl
SOURCE_CLASS_SEPARATION_AUDIT_R16.json
CLAIM_BOUNDARY_AUDIT_R16.json
NO_ACTION_AUDIT_R16.json
VSS_NOT_FACT_SOURCE_AUDIT_R16.json
SECRET_AUDIT_R16.json
KNOWN_LIMITATIONS_R16.md
NEXT_SPRINT_RECOMMENDATIONS_R16.md
R16_JSON_PARSE_REPORT.json
HASH_MANIFEST.json
```

Media packaging rule:
- Small sample metadata/manifests can be packaged.
- Large media should default to `external_media_refs`.
- Packaged media must be hashed in `HASH_MANIFEST.json.files`.
- External media must be recorded in `external_media_refs`.
