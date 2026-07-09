# ENTRY PROMPT — MAIN-CITYBRAIN-METROPOLIS-VSS-OFFLINE-CCTV-DATASET-EXPANSION-R16

Create:

```text
scripts/run_main_citybrain_metropolis_vss_offline_cctv_dataset_expansion_r16.py
```

Output root:

```text
outputs/main_citybrain_metropolis_vss_offline_cctv_dataset_expansion_r16
```

Freeze ZIP:

```text
METROPOLIS_VSS_OFFLINE_CCTV_DATASET_EXPANSION_R16_PACKAGE.zip
```

Required behavior:
1. Load accepted R10-R15 lightweight package if available.
2. Preserve boundaries: DeepStream/Metropolis=`sensor_inferred`; VSS=`model_generated_narrative`; no live CCTV claim; no finding/ticket/dispatch/action/legal/identity claim.
3. Run dataset source gate against candidate matrix.
4. Prefer BMD-45 if no explicit video-dataset license approval exists.
5. If BMD-45 is selected, treat as fixed-CCTV image/frame replay, store attribution/license metadata, and avoid redistributing the full dataset.
6. AI City/VIRAT require explicit `license_gate=PASS` evidence before ingest.

Required outputs:
- `R16_CLOSEOUT_DECISION.json`
- `OFFLINE_DATASET_SOURCE_REGISTRY_R16.json`
- `DATASET_LICENSE_REVIEW_R16.json`
- `OFFLINE_REPLAY_SAMPLE_MANIFEST_R16.json`
- `CAMERA_SOURCE_REGISTRY_UPDATE_R16.json`
- `MEDIA_PROVENANCE_R16.json`
- `CANDIDATE_OBSERVATION_FIXTURE_R16.jsonl`
- `SOURCE_CLASS_SEPARATION_AUDIT_R16.json`
- `CLAIM_BOUNDARY_AUDIT_R16.json`
- `NO_ACTION_AUDIT_R16.json`
- `SECRET_AUDIT_R16.json`
- `HASH_MANIFEST.json`
