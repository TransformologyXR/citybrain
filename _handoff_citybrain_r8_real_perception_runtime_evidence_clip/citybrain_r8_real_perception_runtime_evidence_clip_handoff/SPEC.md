# SPEC — MAIN-CITYBRAIN-R8-REAL-PERCEPTION-RUNTIME-AND-EVIDENCE-CLIP-INTEGRATION

## Objective

Implement a real/replay perception runtime and evidence frame/clip integration lane after R7.

## Product rule

```text
video runtime output = candidate observation
VSS/summary output = review assistance only
frames/clips = evidence refs, not legal proof
case/ticket = draft/sandbox unless explicitly approved
dispatch/control/enforcement = proposal only
execution_status = not_executed by default
```

## Scope

R8 covers:

1. Local/replay media source registry.
2. DeepStream/Metropolis-style runtime adapter or honest runtime-blocked partial.
3. CandidateObservation export from runtime metadata.
4. Evidence frame/clip export and hashing.
5. Optional VSS-style review assistant bridge.
6. WebUI/Kit review integration.
7. Draft/sandbox workflow integration from R7.
8. No-action/proposal boundary.

## Non-goals

R8 does not claim:

- production live monitoring
- final violation detection
- official legal/certified finding
- autonomous ticket/case creation
- direct dispatch/control/enforcement execution
- public/cloud deployment
- production auth/RBAC/security
- safety-critical control
- official affected-building/asset determination

## Required contracts

### PerceptionSource

Minimum fields:

- `source_id`
- `source_kind`
- `uri_or_path`
- `source_mode`
- `camera_or_sensor_id`
- `location_ref`
- `scene_ref`
- `privacy_boundary`
- `retention_policy`
- `source_hash`
- `registered_at`

### RuntimeDetection

Minimum fields:

- `runtime_detection_id`
- `runtime_name`
- `runtime_version`
- `pipeline_config_ref`
- `source_id`
- `frame_index`
- `timestamp`
- `detected_class`
- `confidence`
- `bbox`
- `track_id`
- `zone_ref`
- `raw_metadata_ref`

### CandidateObservation

Minimum fields:

- `candidate_observation_id`
- `source_system`
- `source_type`
- `camera_or_sensor_id`
- `media_ref`
- `frame_ref`
- `clip_ref`
- `timestamp`
- `location_ref`
- `detected_classes`
- `confidence`
- `zone_ref`
- `evidence_refs`
- `limitation_refs`
- `review_state`
- `no_action_state`
- `cannot_claim`
- `packet_hash`

### EvidenceClip

Minimum fields:

- `evidence_id`
- `candidate_observation_id`
- `source_id`
- `media_ref`
- `frame_path`
- `clip_path`
- `timestamp_start`
- `timestamp_end`
- `frame_hash`
- `clip_hash`
- `extraction_method`
- `limitations`

## Acceptance criteria

PASS only if:

- a local/replay media source is registered
- runtime execution or runtime-blocked partial is honestly reported
- candidate observations are generated from runtime or accepted replay metadata
- evidence frame/clip refs are produced and hashed
- CHECK/claimability audit passes
- WebUI/Kit review surface can display candidate observations and evidence
- R7 review promotion gate remains enforced
- draft case/ticket remains sandbox
- action proposal remains `not_executed`
- boundary audit passes
- tests and hash manifest pass

## Expected statuses

- `PASS_R8F_REAL_PERCEPTION_RUNTIME_EVIDENCE_SMOKE_WITH_LIMITATIONS`
- `PARTIAL_R8_RUNTIME_BLOCKED_EVIDENCE_FIXTURES_ONLY`
- `PARTIAL_R8_RUNTIME_OUTPUT_NO_FRAME_CLIP_EXPORT`
- `PARTIAL_R8_EVIDENCE_EXPORT_NO_WEBUI_KIT_REVIEW`
- `FAIL_R8_AUTONOMOUS_ACTION_OR_OFFICIAL_CLAIM_REGRESSION`
- `FAIL_R8_PIXEL_OR_VSS_OUTPUT_USED_AS_TRUTH`
