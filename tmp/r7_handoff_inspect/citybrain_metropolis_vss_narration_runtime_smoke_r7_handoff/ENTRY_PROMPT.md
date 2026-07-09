# ENTRY PROMPT — MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-SMOKE-R7

You are implementing the bounded CityBrain Metropolis/VSS R7 narration runtime smoke.

## Task

Create and run:

```text
scripts/run_main_citybrain_metropolis_vss_narration_runtime_smoke_r7.py
```

Output to:

```text
outputs/main_citybrain_metropolis_vss_narration_runtime_smoke_r7
```

Freeze as:

```text
METROPOLIS_VSS_NARRATION_RUNTIME_SMOKE_R7_PACKAGE.zip
```

## Required behavior

1. Load/validate R2 lineage.
2. Load/validate the latest R6C PASS package or explicit R6C PASS summary.
3. Preserve host allocation:
   - Metropolis/DeepStream on `txr-4070`
   - VSS on Spark
   - `txr-3090` inactive for this chain
4. Probe Spark readiness endpoint.
5. Execute exactly one bounded VSS narration call by one of these methods:
   - `--spark-vss-command`
   - `CITYBRAIN_SPARK_VSS_COMMAND`
   - `--spark-vss-summarize-endpoint`
   - `CITYBRAIN_SPARK_VSS_SUMMARIZE_ENDPOINT`
6. If only `/v1/ready` is configured and no summarize endpoint/command exists, return PARTIAL.
7. Normalize VSS output into `VSS_NARRATION_SIDECAR_R7.jsonl`.
8. Tag VSS output as `source_class=model_generated_narrative`.
9. Do not let VSS alter the R2 candidate event.
10. Run all audits and create a closeout decision.

## CLI shape

Support:

```text
--r2-package PATH
--r6c-package PATH
--media-path PATH
--spark-vss-ready-endpoint URL
--spark-vss-summarize-endpoint URL
--spark-vss-command COMMAND
--output-root PATH
--timeout-seconds 120
--strict
```

Support environment variables:

```text
CITYBRAIN_SPARK_VSS_READY_ENDPOINT
CITYBRAIN_SPARK_VSS_SUMMARIZE_ENDPOINT
CITYBRAIN_SPARK_VSS_COMMAND
CITYBRAIN_R2_PACKAGE
CITYBRAIN_R6C_PACKAGE
CITYBRAIN_R2_MEDIA_PATH
```

## Important

Do not log tokens, API keys, authorization headers, or secret env values.
Do not fabricate narration. Empty or unavailable VSS output is PARTIAL, not PASS.
