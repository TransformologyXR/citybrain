# Roadmap — R10–R15

## R10 — Evidence frame / clip export

Goal: give the R2/R8 candidate event visible media evidence.

Outputs:
- `EVIDENCE_FRAME_MANIFEST_R10.json`
- `EVIDENCE_CLIP_MANIFEST_R10.json` if clip export is possible
- extracted frame/clip files or references
- bbox overlay metadata if available
- `EVIDENCE_FRAME_EXPORT_DECISION_R10.json`

Pass target:

```text
PASS_METROPOLIS_VSS_EVIDENCE_FRAME_EXPORT_R10_WITH_LIMITATIONS
```

## R11 — Offline replay + RTSP/live infrastructure

Goal: use offline video as a live-camera simulator and prepare the future real-camera interface.

Outputs:
- replay source manifest
- local RTSP/file-replay config
- future camera endpoint contract
- connectivity probe report
- `RTSP_REPLAY_INFRA_DECISION_R11.json`

Pass target:

```text
PASS_METROPOLIS_VSS_RTSP_REPLAY_INFRA_R11_WITH_LIMITATIONS
```

## R12 — Multi-zone / multi-class

Goal: move beyond one zone / one class if metadata supports it.

Outputs:
- zone definitions
- class policy
- multi-zone observation JSONL
- multi-class audit
- `MULTIZONE_MULTICLASS_DECISION_R12.json`

Pass target:

```text
PASS_METROPOLIS_VSS_MULTIZONE_MULTICLASS_R12_WITH_LIMITATIONS
```

Partial target if only one class is present:

```text
PARTIAL_METROPOLIS_VSS_MULTIZONE_READY_MULTICLASS_NOT_OBSERVED
```

## R13 — Human-review UI packet

Goal: export a frontend-ready review packet without implementing UI.

Outputs:
- candidate card packet
- evidence viewer packet
- review action state packet
- limitation/cannot-claim labels
- `HUMAN_REVIEW_UI_PACKET_DECISION_R13.json`

Pass target:

```text
PASS_METROPOLIS_VSS_HUMAN_REVIEW_UI_PACKET_R13_WITH_LIMITATIONS
```

## R14 — Camera/source registry and provenance

Goal: make media provenance explicit.

Outputs:
- camera/source registry
- media provenance records
- license/source status
- timing model
- location/zone confidence
- secret/privacy audit
- `CAMERA_SOURCE_REGISTRY_DECISION_R14.json`

Pass target:

```text
PASS_METROPOLIS_VSS_CAMERA_SOURCE_REGISTRY_PROVENANCE_R14_WITH_LIMITATIONS
```

## R15 — Sprint closeout

Goal: freeze the combined sprint.

Outputs:
- final decision
- R10–R15 lineage
- final audits
- known limitations
- next sprint recommendations
- freeze ZIP

Pass target:

```text
PASS_METROPOLIS_VSS_EVIDENCE_REPLAY_READINESS_SPRINT_R15_WITH_LIMITATIONS
```
