# MAIN-CITYBRAIN-D8-CAMERA-VIDEO-DONOR-SOURCE-SCOUT

Goal: find bounded, licensed camera/video donors for D7/VSS demonstration without live surveillance claims.

Candidates:
- Singapore LTA traffic images if credentials/access are valid
- Chicago sensor/image/video alternatives if available and licensed
- Helsinki visual mesh only as backdrop, not camera/video evidence
- small public/open demo MP4s only if unrelated and clearly labelled as demo sample media

Outputs:
- CAMERA_VIDEO_SOURCE_INVENTORY.json
- ACCESS_AND_AUTH_REPORT.json
- LICENSE_AND_PRIVACY_REPORT.md
- SAMPLE_MEDIA_MANIFEST.json
- CAMERA_METADATA_SCHEMA.json
- DEMO_MEDIA_BOUNDARY_LABELS.json
- HASH_MANIFEST.json

Hard rules:
- Do not use private/security CCTV.
- Do not infer identity, biometrics, license plates, or people attributes.
- Candidate observations only; no alerts, monitoring, enforcement, dispatch, or legal finding.
- If an API key is required and absent/invalid, status is AUTH_MISSING, not PASS.
