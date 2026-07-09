# R14 — Camera / Source Registry and Media Provenance

## Goal

Make media provenance explicit.

## Camera/source registry fields

```json
{
  "camera_source_id": "string",
  "source_kind": "offline_file | rtsp_replay | live_rtsp_future",
  "host": "txr-4070",
  "uri_or_path": "string",
  "uri_secret_redacted": true,
  "timezone": "string",
  "location_known": false,
  "location_confidence": "unknown | candidate | verified",
  "source_owner": "string",
  "license_status": "local_sample | public_dataset_pending_review | private_future",
  "privacy_status": "sample_or_public_non_production",
  "retention_policy": "bounded_artifact_only",
  "hash": "sha256"
}
```

## Provenance fields

- media_source_id
- frame/time references
- file hash
- extraction command
- package hash
- source class
- review state
- limitations
