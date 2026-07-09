# ROADMAP — MAIN-CITYBRAIN-R8-REAL-PERCEPTION-RUNTIME-AND-EVIDENCE-CLIP-INTEGRATION

## Sprint theme

```text
From fixture perception smoke to real/replay perception runtime evidence
```

## Baseline

R7 is accepted:

```text
PASS_R7E_PERCEPTION_TO_REVIEW_WORKFLOW_SMOKE_WITH_LIMITATIONS
```

R7 proved candidate observation ingress, human review promotion gate, draft/sandbox case-ticket adapter, proposal-only action boundary, and integrated local/replay smoke.

## R8 lanes

### R8A — Source/media readiness and camera registry

Task:

```text
MAIN-CITYBRAIN-R8A-PERCEPTION-SOURCE-MEDIA-READINESS
```

Goal:

Prepare the media/source foundation for real perception runtime.

Minimum scope:

- camera/source registry
- media inventory
- replay clip refs
- timestamps
- location/scene/entity hints
- privacy/boundary notes
- evidence retention notes

Acceptance:

- at least 1 replay/local media source is registered
- all media evidence refs are local/test/replay
- no production live monitoring claim

### R8B — DeepStream/Metropolis runtime adapter

Task:

```text
MAIN-CITYBRAIN-R8B-DEEPSTREAM-METROPOLIS-RUNTIME-ADAPTER
```

Goal:

Run or wrap a local/replay DeepStream/Metropolis-style detection pipeline.

Minimum scope:

- local MP4/file source or RTSP replay source
- pipeline config record
- detection metadata output
- class/confidence/timestamp/frame refs
- optional tracking IDs if available
- raw runtime log capture
- candidate observation export

Acceptance:

- runtime is actually executed or honest partial states why not
- at least one candidate observation output if runtime succeeds
- no final violation/legal/official action claim

### R8C — Evidence frame/clip exporter

Task:

```text
MAIN-CITYBRAIN-R8C-EVIDENCE-FRAME-CLIP-EXPORTER
```

Goal:

Attach visual evidence to candidate observations.

Minimum scope:

- frame snapshot export
- optional clip slice export
- evidence manifest
- media SHA/hash
- frame timestamp
- source/camera linkage
- detection metadata linkage

Acceptance:

- candidate observations reference evidence frames/clips
- evidence files exist or a blocked limitation is explicit
- hashes verify

### R8D — VSS review assist / video summarization bridge

Task:

```text
MAIN-CITYBRAIN-R8D-VSS-REVIEW-ASSIST-BRIDGE
```

Goal:

Use VSS-style outputs only as review assistance, not truth.

Minimum scope:

- VSS answer/summary/search result fixture or runtime output
- source video ref
- cited segment/frame refs
- uncertainty/limitations
- no unsupported fact creation
- CHECK validation

Acceptance:

- VSS output is stored as assistant evidence/candidate narrative
- not used as official truth
- unsupported summaries are downgraded or abstained

### R8E — CityBrain review integration

Task:

```text
MAIN-CITYBRAIN-R8E-PERCEPTION-EVIDENCE-TO-REVIEW-INTEGRATION
```

Goal:

Connect candidate observations and evidence clips to the R6/R7 review cockpit.

Minimum scope:

- candidate observation card
- frame/clip evidence view
- CHECK/claimability view
- review state controls
- draft case/ticket path remains sandbox
- action proposal remains `not_executed`

Acceptance:

- WebUI/Kit can surface candidate observation + evidence
- human review promotion gate still enforced
- no official submission/execution

### R8F — Integrated runtime smoke

Task:

```text
MAIN-CITYBRAIN-R8F-REAL-PERCEPTION-RUNTIME-EVIDENCE-SMOKE
```

Goal:

End-to-end smoke:

```text
local/replay video source
→ DeepStream/Metropolis/VSS-style runtime or honest partial
→ candidate observation
→ frame/clip evidence
→ CityBrain review packet
→ WebUI/Kit review
→ draft/sandbox case-ticket
→ proposal-only action remains not_executed
```

Expected status:

```text
PASS_R8F_REAL_PERCEPTION_RUNTIME_EVIDENCE_SMOKE_WITH_LIMITATIONS
```

or honest partial if runtime is blocked.
