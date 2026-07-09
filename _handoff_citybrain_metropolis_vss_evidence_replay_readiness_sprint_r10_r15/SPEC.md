# SPEC — MAIN-CITYBRAIN-METROPOLIS-VSS-EVIDENCE-REPLAY-READINESS-SPRINT-R10-R15

## Objective

Extend the closed R9 Metropolis/VSS lane into a second bounded sprint that completes the five next-sprint items together:

1. Evidence frame / clip export for the R2/R8 candidate event.
2. Offline pre-recorded CCTV-style replay source plus live/RTSP readiness infrastructure.
3. Multi-zone and, where real metadata supports it, multi-class candidate observations.
4. Human-review UI packet integration.
5. Camera/source registry and media provenance hardening.

## Sprint milestones

```text
R10  Offline video source scout + evidence frame/clip export
R11  RTSP/live-source infrastructure preflight using offline replay
R12  Multi-zone / multi-class candidate observation expansion
R13  Human-review UI packet export
R14  Camera/source registry and media provenance
R15  Sprint closeout freeze
```

## Non-goals

- Production monitoring.
- Live CCTV deployment against a real camera.
- Legal/certified violation finding.
- Official case/ticket creation.
- Dispatch, routing, control, enforcement, or alert command.
- Identity or biometric inference.
- VSS as a fact source.
- Synthetic detection classes not backed by actual metadata.

## Required host allocation

```json
{
  "txr_4070": {
    "role": "DeepStream / Metropolis media inference and evidence export",
    "source_class": "sensor_inferred",
    "status": "proven_by_R2_R8_R9"
  },
  "spark_2445": {
    "role": "VSS / LVS / RT-VLM narration only",
    "source_class": "model_generated_narrative",
    "status": "proven_by_R6C_R7_R8_R9"
  },
  "txr_3090": {
    "role": "not active for this Metropolis/VSS chain",
    "status": "inactive"
  }
}
```

## Default offline source strategy

Use the existing DeepStream bundled sample media immediately for deterministic local continuity, then optionally add a public dataset source only after license and download practicality are verified.

Preferred order:

1. Existing local DeepStream sample, already proven in R2.
2. AI City / CityFlowV2 traffic camera video if download/license is acceptable.
3. AI City WTS traffic-safety videos if the sprint needs richer VSS narration/captioning input.
4. VIRAT-like surveillance data only if license and source authenticity are verified.

## Acceptance target

```text
PASS_METROPOLIS_VSS_EVIDENCE_REPLAY_READINESS_SPRINT_R15_WITH_LIMITATIONS
```

Acceptable partial:

```text
PARTIAL_METROPOLIS_VSS_EVIDENCE_FRAME_AND_REPLAY_READY_LIVE_CAMERA_PENDING
```
