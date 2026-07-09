# ENTRY PROMPT — MAIN-CITYBRAIN-METROPOLIS-VSS-SPARK-SPLIT-HOST-READINESS-R6D

You are implementing the next CityBrain Metropolis/VSS media-lane gate.

Context:

- R2 proved DeepStream/Metropolis object metadata export on `txr-4070`.
- R2 used the DeepStream 8.0 container, `gie-kitti-output-dir`, bundled `sample_1080p_h264.mp4`, and exported 24 `car` records normalized as `vehicle_presence_candidate`.
- R3/R4/R5/R6/R6B/R6C kept VSS guarded but not configured.
- VSS is now being installed on Spark / DGX Spark.
- `txr-3090` is not active for this Metropolis/VSS chain.

Implement:

```text
scripts/run_main_citybrain_metropolis_vss_spark_split_host_readiness_r6d.py
```

Output root:

```text
outputs/main_citybrain_metropolis_vss_spark_split_host_readiness_r6d
```

Freeze ZIP:

```text
METROPOLIS_VSS_SPARK_SPLIT_HOST_READINESS_R6D_PACKAGE.zip
```

Required behavior:

1. Read prior R6C/R2 lineage if present.
2. Emit `RUNTIME_HOST_ALLOCATION_R6D.json` locking:
   - `txr-4070` for DeepStream/Metropolis
   - `Spark / DGX Spark` as intended VSS host once installed
   - `txr-3090` not active for this chain
3. Emit `SPARK_VSS_RUNTIME_CONFIG_R6D.json` from CLI/env inspection.
4. Emit `SPARK_VSS_CONNECTIVITY_PROBE_CONTRACT_R6D.json` describing, but not fabricating, the required probe.
5. Emit `CROSS_HOST_PAYLOAD_CONTRACT_R6D.json` defining the R2 evidence subset that may be sent to VSS.
6. Emit `R7_READINESS_GATE_R6D.json` with `r7_ready=false` unless a real Spark VSS runtime is configured and connectivity has passed.
7. Emit audits:
   - source-class separation
   - claim-boundary
   - no-action
   - secret audit
   - host-allocation audit
8. Emit parse report and hash manifest.

CLI/env keys to support:

```text
--spark-vss-command
--spark-vss-endpoint
CITYBRAIN_SPARK_VSS_COMMAND
CITYBRAIN_SPARK_VSS_ENDPOINT
```

Do not emit narration in R6D. R7 is the first allowed narration smoke, and only after R6D/R6C-style readiness passes.
