# PROMPT — MAIN-CITYBRAIN-R8-REAL-PERCEPTION-RUNTIME-AND-EVIDENCE-CLIP-INTEGRATION

You are implementing `MAIN-CITYBRAIN-R8-REAL-PERCEPTION-RUNTIME-AND-EVIDENCE-CLIP-INTEGRATION`.

## Context

R7 is accepted:

```text
PASS_R7E_PERCEPTION_TO_REVIEW_WORKFLOW_SMOKE_WITH_LIMITATIONS
```

R8 must move from fixture/sandbox perception smoke to real/replay runtime evidence integration.

Use DeepStream/Metropolis/VSS-style outputs as candidate observations and review assistance only.

## Create runner

```text
scripts/run_main_citybrain_r8_real_perception_runtime_evidence_clip_integration.py
```

Output root:

```text
outputs/main_citybrain_r8_real_perception_runtime_evidence_clip_integration
```

## Implement

### 1. Source/media readiness

Create source registry and media inventory.

Required:

- at least 1 local/replay media source
- source hash
- camera/source ID
- timestamp/location/scene refs where available
- privacy and retention notes

### 2. Runtime adapter

Attempt to run or wrap a local/replay DeepStream/Metropolis-style runtime.

If runtime cannot run, do not fake it. Produce an honest partial with blocked reason and use accepted replay metadata fixtures.

Required:

- pipeline config ref
- runtime logs
- detection metadata
- class/confidence/timestamp/frame refs
- candidate observation export

### 3. Evidence frame/clip export

Export frames and optional clips from source media.

Required:

- frame evidence file
- optional clip evidence file
- evidence manifest
- SHA hashes
- candidate observation linkage

### 4. VSS review assist bridge

If VSS runtime or fixture is available, include:

- video summary/search/Q&A result
- segment/frame refs
- uncertainty/limitations
- CHECK validation

VSS output is not truth.

### 5. Review integration

Feed candidate observation + evidence into CityBrain review surface.

Required:

- WebUI/Kit candidate observation card
- evidence refs visible
- limitations visible
- review state visible
- no-action visible
- R7 promotion gate enforced

### 6. Draft/proposal path

Generate sandbox/draft workflow packet and proposal-only action object only after review promotion.

Required:

- no official submission
- no execution
- `execution_status = not_executed`

## Required reports

Write:

```text
ENTRY_PROMPT.md
README.md
DECISION.json
PERCEPTION_SOURCE_REGISTRY_AUDIT.json
RUNTIME_ADAPTER_EXECUTION_REPORT.json
RUNTIME_DETECTION_METADATA_AUDIT.json
CANDIDATE_OBSERVATION_EXPORT_AUDIT.json
EVIDENCE_FRAME_CLIP_EXPORT_AUDIT.json
VSS_REVIEW_ASSIST_AUDIT.json
CHECK_CLAIMABILITY_AUDIT.json
WEBUI_KIT_REVIEW_INTEGRATION_AUDIT.json
DRAFT_WORKFLOW_BOUNDARY_AUDIT.json
ACTION_PROPOSAL_BOUNDARY_AUDIT.json
ONE_TRUTH_PACKET_AUDIT.json
BOUNDARY_AUDIT.json
TEST_LOG.txt
LIMITATIONS.md
HASH_MANIFEST.txt
```

Suggested folders:

```text
source_media/
runtime_logs/
runtime_metadata/
candidate_observations/
evidence_frames/
evidence_clips/
vss_review_assist/
review_packets/
draft_workflow_packets/
action_proposals/
webui_evidence/
kit_evidence/
source_refs/
```

## Tests

Add tests for:

- source registry
- runtime detection metadata schema
- candidate observation export
- evidence frame/clip hashing
- VSS output not used as truth
- review gate still required
- draft workflow remains sandbox
- action proposal remains not_executed
- forbidden claims

Run full discovery.

## Decision

Use `PASS_R8F_REAL_PERCEPTION_RUNTIME_EVIDENCE_SMOKE_WITH_LIMITATIONS` only if real/replay source, runtime/metadata, evidence export, candidate observations, review integration, draft/proposal boundary, tests, and manifest pass.

Use partial honestly if the runtime cannot run and only fixtures are used.

Fail if autonomous action, official submission, final legal/violation claim, or pixel/VSS-derived truth is introduced.
