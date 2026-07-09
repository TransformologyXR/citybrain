# ENTRY PROMPT — Codex / Implementation Agent

You are implementing the next Metropolis/VSS sprint after R9.

Task:

```text
MAIN-CITYBRAIN-METROPOLIS-VSS-EVIDENCE-REPLAY-READINESS-SPRINT-R10-R15
```

Use the R9 package as the source of truth. Preserve the final R9 boundary:

- DeepStream / Metropolis on `txr-4070` is `sensor_inferred`.
- Spark VSS on `spark-2445` is `model_generated_narrative` only.
- `txr-3090` is inactive for this chain.
- Human review is required.
- No official record, ticket, action, dispatch, identity claim, legal finding, or certified finding.

Implement runners:

```text
scripts/run_main_citybrain_metropolis_vss_evidence_frame_export_r10.py
scripts/run_main_citybrain_metropolis_vss_rtsp_replay_infra_r11.py
scripts/run_main_citybrain_metropolis_vss_multizone_multiclass_r12.py
scripts/run_main_citybrain_metropolis_vss_human_review_ui_packet_r13.py
scripts/run_main_citybrain_metropolis_vss_camera_source_registry_r14.py
scripts/run_main_citybrain_metropolis_vss_evidence_replay_readiness_closeout_r15.py
```

Default input:

```text
outputs/main_citybrain_metropolis_vss_sprint_closeout_r9/METROPOLIS_VSS_SPRINT_CLOSEOUT_R9_PACKAGE.zip
```

Default output root:

```text
outputs/main_citybrain_metropolis_vss_evidence_replay_readiness_sprint_r10_r15
```

Expected final ZIP:

```text
METROPOLIS_VSS_EVIDENCE_REPLAY_READINESS_SPRINT_R10_R15_PACKAGE.zip
```

## Required behavior

### R10
Export representative frame(s) and/or bounded clip reference(s) for the selected R2/R8 candidate event.

### R11
Prepare an offline replay source that can simulate a live camera using file-to-RTSP or equivalent local replay. If no RTSP service is available, emit a contract-ready partial with file replay proven.

### R12
Add multi-zone candidate observation support. Add multi-class only where actual DeepStream metadata supports additional classes. Do not invent classes.

### R13
Emit a UI-ready human-review packet. This is not frontend implementation. It is a stable packet contract.

### R14
Emit camera/source registry and media provenance records.

### R15
Freeze sprint with final lineage, audits, known limitations, and next-sprint recommendation.

## Status rules

PASS only if artifacts are real and verified.

PARTIAL if infrastructure is contract-ready but a live camera or external dataset is not available.

FAIL if any output creates or implies:
- confirmed violation
- legal/certified finding
- identity/biometric inference
- official case/ticket
- dispatch/routing/control/enforcement
- alert as operational command
- automated action
- VSS as a fact source
